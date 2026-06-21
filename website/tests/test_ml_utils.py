"""Unit tests for website.utils.ml_utils (#1278, item 5).

Pure helper functions used across views and templates (school/department
abbreviations, video embeds, forum-name cleaning, fuzzy matching). No DB.
The model- and datetime-coupled helpers (sort_projects_*, choose_banners*)
are intentionally left for integration-style tests.
"""

from datetime import date

from django.test import SimpleTestCase

from website.utils.ml_utils import (
    clean_forum_name,
    create_acronym,
    get_closest_match,
    get_department_abbreviated,
    get_school_abbreviated,
    get_video_embed,
    slugify_max,
    weighted_choice,
)


class SlugifyMaxTests(SimpleTestCase):
    def test_short_text_passes_through(self):
        self.assertEqual(slugify_max("Hello World"), "hello-world")

    def test_truncates_without_exceeding_max_length(self):
        result = slugify_max("Alpha Beta Gamma Delta", max_length=10)
        self.assertLessEqual(len(result), 10)
        self.assertFalse(result.endswith("-"), "must not end on a partial-word hyphen")


class CreateAcronymTests(SimpleTestCase):
    def test_first_letter_of_each_word(self):
        self.assertEqual(create_acronym("human computer interaction"), "hci")


class GetSchoolAbbreviatedTests(SimpleTestCase):
    def test_washington_is_uw(self):
        self.assertEqual(get_school_abbreviated("University of Washington"), "UW")

    def test_maryland_is_umd(self):
        self.assertEqual(get_school_abbreviated("University of Maryland"), "UMD")

    def test_other_school_falls_back_to_acronym(self):
        # " of " is dropped before acronyming, so "University of Foo Bar" -> UFB.
        self.assertEqual(get_school_abbreviated("University of Foo Bar"), "UFB")


class GetDepartmentAbbreviatedTests(SimpleTestCase):
    def test_cse(self):
        self.assertEqual(
            get_department_abbreviated("Computer Science & Engineering"), "CSE"
        )

    def test_allen_school_is_cse(self):
        self.assertEqual(get_department_abbreviated("Paul G. Allen School"), "CSE")

    def test_ischool(self):
        self.assertEqual(get_department_abbreviated("The Information School"), "iSchool")

    def test_hcde(self):
        self.assertEqual(get_department_abbreviated("HCDE"), "HCDE")


class GetVideoEmbedTests(SimpleTestCase):
    def test_youtube_short_url(self):
        embed = get_video_embed("https://youtu.be/i0IDbHGir-8")
        self.assertTrue(embed.startswith("https://youtube.com/embed"))
        self.assertIn("i0IDbHGir-8", embed)

    def test_youtube_watch_url(self):
        # The watch?v= form must resolve to /embed/<id>, NOT /embed/watch?v=<id>.
        self.assertEqual(
            get_video_embed("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "https://youtube.com/embed/dQw4w9WgXcQ?showinfo=0&iv_load_policy=3",
        )

    def test_youtube_share_url_with_si_param(self):
        # YouTube "Share" links carry a ?si=... tracking token. It must be
        # dropped, not concatenated, so the embed URL has a single '?' and the
        # player actually loads (regression: ...?si=x?showinfo=0).
        embed = get_video_embed("https://youtu.be/i0IDbHGir-8?si=AbC123dEf")
        self.assertEqual(
            embed, "https://youtube.com/embed/i0IDbHGir-8?showinfo=0&iv_load_policy=3"
        )
        self.assertEqual(embed.count("?"), 1, "embed URL must have exactly one '?'")
        self.assertNotIn("si=", embed)

    def test_vimeo_url(self):
        self.assertEqual(
            get_video_embed("https://vimeo.com/164630179"),
            "https://player.vimeo.com/video/164630179",
        )

    def test_unknown_service(self):
        self.assertTrue(
            get_video_embed("https://example.com/clip").startswith(
                "unknown video service"
            )
        )


class CleanForumNameTests(SimpleTestCase):
    def test_strips_proceedings_of_and_trailing_year(self):
        self.assertEqual(clean_forum_name("Proceedings of CHI 2022"), "CHI")

    def test_plain_name_with_year(self):
        self.assertEqual(clean_forum_name("CHI 2022"), "CHI")

    def test_name_without_decoration_unchanged(self):
        self.assertEqual(clean_forum_name("ASSETS"), "ASSETS")


class GetClosestMatchTests(SimpleTestCase):
    def test_returns_closest_above_cutoff(self):
        self.assertEqual(
            get_closest_match("aple", ["apple", "banana"], cutoff=0.5), "apple"
        )

    def test_returns_none_when_nothing_within_cutoff(self):
        self.assertIsNone(get_closest_match("xyz", ["apple", "banana"], cutoff=0.8))


class WeightedChoiceTests(SimpleTestCase):
    def test_single_choice_is_deterministic(self):
        self.assertEqual(weighted_choice([("only", 1)]), "only")

    def test_zero_weight_option_is_never_chosen(self):
        # The non-zero-weight option spans the whole [0, total] range.
        self.assertEqual(weighted_choice([("yes", 1), ("never", 0)]), "yes")
