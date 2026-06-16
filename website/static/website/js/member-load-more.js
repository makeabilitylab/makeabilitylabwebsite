/**
 * MemberLoadMore — drives the per-section "Load more" / "Load all" controls on
 * the member profile page (issue #1110).
 *
 * Each artifact section (Projects / Papers / Videos / Talks) renders the DESKTOP
 * count of cards on first paint. On phones a CSS rule (.is-collapsed in
 * member.css) hides the overflow so only the mobile count shows. A
 * ".see-more-controls" block below each grid holds two buttons:
 *
 *   - "Load N more <type>": ONE robust path — it always lifts the mobile cap
 *     (revealing any already-rendered-but-CSS-hidden cards) and, if the server
 *     still has more, AJAX-appends the next batch from website:member_artifacts.
 *     The label's N is recomputed to be EXACTLY how many cards the next click
 *     will add (revealed + fetched), so it stays accurate on phone and desktop.
 *   - "Load all <total> <type>": fetches every remaining item in one request
 *     (?all=1). Hidden whenever "Load more" would already load the rest.
 *
 * Appended cards are the SAME snippet HTML the page renders on first paint, so
 * we just re-run the behaviors that bind at init time — VideoAge and
 * CitationPopover (both idempotent / guarded) — after each append.
 *
 * Accessibility: after content appears, focus moves to the first newly shown
 * card and a polite live region announces what loaded. Controls are real
 * <button>s with aria-controls pointing at their grid.
 *
 * Progressive-enhancement tradeoff: the controls render with the `hidden`
 * attribute and are only un-hidden by this script. With JS disabled they stay
 * hidden, so a no-JS phone visitor sees only the mobile count and cannot expand
 * (accepted — see member.html for the rationale).
 *
 * @author Makeability Lab
 */
const MemberLoadMore = (function () {
  'use strict';

  // Keep in sync with the single-column breakpoint in member.css, below which
  // grids are CSS-capped to the mobile count.
  const MOBILE_MEDIA = '(max-width: 576px)';

  // Display names for labels/announcements, keyed by data-artifact-type.
  const LABELS = {
    projects: 'projects',
    publications: 'papers',
    videos: 'videos',
    talks: 'talks',
  };

  let liveRegion = null;

  function isMobile() {
    return window.matchMedia(MOBILE_MEDIA).matches;
  }

  function label(type) {
    return LABELS[type] || 'items';
  }

  /** Lazily create a single visually-hidden polite live region. */
  function getLiveRegion() {
    if (liveRegion) {
      return liveRegion;
    }
    liveRegion = document.createElement('div');
    liveRegion.setAttribute('role', 'status');
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.style.cssText =
      'position:absolute;width:1px;height:1px;margin:-1px;padding:0;' +
      'overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0;';
    document.body.appendChild(liveRegion);
    return liveRegion;
  }

  function announce(message) {
    getLiveRegion().textContent = message;
  }

  /** Read a section's state from its .see-more-controls wrapper. */
  function readCtx(controls) {
    return {
      controls: controls,
      grid: document.getElementById(controls.dataset.grid),
      memberId: controls.dataset.memberId,
      type: controls.dataset.artifactType,
      total: parseInt(controls.dataset.total, 10),
      pageSize: parseInt(controls.dataset.pageSize, 10),
      mobileSize: parseInt(controls.dataset.mobileSize, 10),
      rendered: parseInt(controls.dataset.rendered, 10),
    };
  }

  /** How many cards are currently VISIBLE, accounting for the mobile CSS cap. */
  function shownCount(c) {
    const capped = c.grid.classList.contains('is-collapsed') && isMobile();
    return capped ? Math.min(c.mobileSize, c.rendered) : c.rendered;
  }

  /** Exactly how many cards the next "Load more" click will add: the
   *  already-rendered-but-hidden ones it reveals, plus one fetched batch. */
  function nextMoreYield(c) {
    const revealed = c.rendered - shownCount(c);
    const fetched = Math.min(c.pageSize, c.total - c.rendered);
    return revealed + fetched;
  }

  /** Recompute the controls' visibility and the two button labels. */
  function refresh(controls) {
    const c = readCtx(controls);
    if (!c.grid) {
      return;
    }
    const remaining = c.total - shownCount(c);
    if (remaining <= 0) {
      controls.hidden = true;
      return;
    }
    controls.hidden = false;

    const moreBtn = controls.querySelector('[data-load-more]');
    const allBtn = controls.querySelector('[data-load-all]');
    if (moreBtn) {
      moreBtn.textContent = 'Load ' + nextMoreYield(c) + ' more ' + label(c.type);
    }
    if (allBtn) {
      // No point offering "Load all" if "Load more" already shows the rest.
      if (nextMoreYield(c) >= remaining) {
        allBtn.hidden = true;
      } else {
        allBtn.hidden = false;
        allBtn.textContent = 'Load all ' + c.total + ' ' + label(c.type);
      }
    }
  }

  function cardChildren(grid) {
    return Array.prototype.filter.call(grid.children, function (n) {
      return n.nodeType === 1;
    });
  }

  function focusCard(card) {
    if (!card) {
      return;
    }
    card.setAttribute('tabindex', '-1');
    card.focus({ preventScroll: true });
  }

  /** Re-run init-time behaviors on freshly appended snippets (both idempotent). */
  function reinitBehaviors() {
    if (typeof VideoAge !== 'undefined') {
      VideoAge.init();
    }
    if (typeof CitationPopover !== 'undefined') {
      CitationPopover.init('.publication-citation-link');
    }
  }

  /** Disable both buttons during a fetch and show a spinner on the one the user
   *  clicked, so a slow "Load all" (rendering 100+ cards) gives clear feedback. */
  function setBusy(controls, busy, clickedBtn) {
    const buttons = controls.querySelectorAll('button');
    Array.prototype.forEach.call(buttons, function (b) {
      b.disabled = busy;
    });
    if (busy) {
      controls.setAttribute('aria-busy', 'true');
      if (clickedBtn) {
        clickedBtn.innerHTML =
          '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Loading…';
      }
    } else {
      controls.removeAttribute('aria-busy');
      // Labels (and so the spinner) are restored by refresh(); nothing to do.
    }
  }

  /**
   * Handle a click on either control.
   * @param {HTMLElement} controls - the .see-more-controls wrapper
   * @param {boolean} all - true for "Load all", false for "Load more"
   * @param {HTMLElement} btn - the button that was clicked (for the spinner)
   */
  function handleClick(controls, all, btn) {
    const c = readCtx(controls);
    if (!c.grid) {
      return;
    }

    const expectedYield = all
      ? c.total - shownCount(c)
      : nextMoreYield(c);
    const firstHiddenIndex = shownCount(c); // first card not yet visible

    // Always lift the mobile cap first: this reveals any rendered-but-hidden
    // cards (the cheap part) so they don't sit invisibly above appended ones.
    c.grid.classList.remove('is-collapsed');

    // If the server has nothing more, the click was a pure reveal — done.
    if (c.rendered >= c.total) {
      const cards = cardChildren(c.grid);
      focusCard(cards[firstHiddenIndex] || null);
      announce('Showing all ' + c.total + ' ' + label(c.type) + '.');
      refresh(controls);
      return;
    }

    fetchMore(controls, c, all, expectedYield, firstHiddenIndex, btn);
  }

  function fetchMore(controls, c, all, expectedYield, firstHiddenIndex, btn) {
    setBusy(controls, true, btn);

    const url = '/member/' + encodeURIComponent(c.memberId) +
      '/artifacts/' + encodeURIComponent(c.type) +
      '/?offset=' + encodeURIComponent(c.rendered) +
      (all ? '&all=1' : '');

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (response) {
        if (!response.ok) {
          throw new Error('Request failed: ' + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        const temp = document.createElement('div');
        temp.innerHTML = data.html;
        const newCards = Array.prototype.filter.call(temp.childNodes, function (n) {
          return n.nodeType === 1;
        });
        const cardsBefore = cardChildren(c.grid);
        newCards.forEach(function (card) {
          c.grid.appendChild(card);
        });

        controls.dataset.rendered = String(data.next_offset);
        reinitBehaviors();
        setBusy(controls, false);

        if (!data.has_more) {
          controls.remove();
        } else {
          refresh(controls);
        }

        announce('Loaded ' + expectedYield + ' more ' + label(c.type) + '. ' +
          Math.min(data.next_offset, c.total) + ' of ' + c.total + ' shown.');
        // Focus the first card that became visible (a revealed one if there were
        // any, otherwise the first freshly fetched one).
        focusCard(cardsBefore[firstHiddenIndex] || newCards[0] || null);
      })
      .catch(function (error) {
        setBusy(controls, false);
        refresh(controls);
        announce('Sorry, something went wrong loading more ' + label(c.type) +
          '. Please try again.');
        if (window.console && console.error) {
          console.error('MemberLoadMore:', error);
        }
      });
  }

  function init() {
    const blocks = Array.prototype.slice.call(
      document.querySelectorAll('.see-more-controls')
    );
    if (blocks.length === 0) {
      return;
    }

    blocks.forEach(function (controls) {
      refresh(controls); // un-hide + label where there's more to show
      const moreBtn = controls.querySelector('[data-load-more]');
      const allBtn = controls.querySelector('[data-load-all]');
      if (moreBtn) {
        moreBtn.addEventListener('click', function () {
          handleClick(controls, false, moreBtn);
        });
      }
      if (allBtn) {
        allBtn.addEventListener('click', function () {
          handleClick(controls, true, allBtn);
        });
      }
    });

    // Crossing the mobile/desktop breakpoint changes how many cards count as
    // visible, so recompute labels/visibility for any controls still on-page.
    const mql = window.matchMedia(MOBILE_MEDIA);
    const onChange = function () {
      blocks.forEach(function (controls) {
        if (controls.isConnected) {
          refresh(controls);
        }
      });
    };
    if (mql.addEventListener) {
      mql.addEventListener('change', onChange);
    } else if (mql.addListener) {
      mql.addListener(onChange); // Safari < 14
    }
  }

  return { init: init };
})();
