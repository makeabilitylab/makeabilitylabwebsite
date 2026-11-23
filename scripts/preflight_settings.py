"""Deploy preflight: can Django's settings load with this host's config.ini?

Run by the deploy workflows in a throwaway container, before the running site
is replaced:

    docker compose run --rm --no-deps -T website python scripts/preflight_settings.py

Exit status 0 means the settings imported. Anything else fails the deploy job.

Why a script instead of ``python -c "import makeabilitylab.settings"``: this
output goes to a PUBLIC GitHub Actions log, and an uncaught traceback can carry
text from config.ini (configparser quotes the bad line or value in its
errors). So this prints the exception's type, and its message only for
ImproperlyConfigured, whose messages settings.py writes without any values.
It never prints a traceback.
"""
import os
import sys

# Running a file puts scripts/ on sys.path, not the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    try:
        import makeabilitylab.settings  # noqa: F401
    except Exception as e:  # deliberately broad: nothing may escape as a traceback
        from django.core.exceptions import ImproperlyConfigured

        print(f"PREFLIGHT FAILED: settings did not load ({type(e).__name__}).")
        if isinstance(e, ImproperlyConfigured):
            print(f"Reason: {e}")
        else:
            print("Details are withheld from this public log; reproduce locally "
                  "or see docs/DEPLOYMENT.md.")
        return 1
    print("PREFLIGHT OK: settings loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
