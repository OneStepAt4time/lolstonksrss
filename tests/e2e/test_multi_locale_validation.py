"""Multi-locale RSS feed validation tests for all 20 Riot locales."""

import feedparser
import httpx
import pytest

RIOT_LOCALES = [
    "en-us",
    "en-gb",
    "es-es",
    "es-mx",
    "fr-fr",
    "de-de",
    "it-it",
    "pt-br",
    "ru-ru",
    "tr-tr",
    "pl-pl",
    "ja-jp",
    "ko-kr",
    "zh-cn",
    "zh-tw",
    "ar-ae",
    "vi-vn",
    "th-th",
    "id-id",
    "ph-ph",
]

EXPECTED_LANGUAGES = {
    "en-us": "en",
    "en-gb": "en",
    "it-it": "it",
    "es-es": "es",
    "es-mx": "es",
    "fr-fr": "fr",
    "de-de": "de",
    "pt-br": "pt",
    "ru-ru": "ru",
    "tr-tr": "tr",
    "pl-pl": "pl",
    "ja-jp": "ja",
    "ko-kr": "ko",
    "zh-cn": "zh",
    "zh-tw": "zh",
    "ar-ae": "ar",
    "vi-vn": "vi",
    "th-th": "th",
    "id-id": "id",
    "ph-ph": "tl",
}


class LocaleFeedValidator:
    @staticmethod
    def validate_http_200(response: httpx.Response) -> None:
        assert response.status_code == 200

    @staticmethod
    def validate_xml_wellformed(feed: feedparser.FeedParserDict) -> None:
        assert feed.bozo == 0

    @staticmethod
    def validate_rss_version(feed: feedparser.FeedParserDict) -> None:
        assert feed.version == "rss20"


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.locale
@pytest.mark.parametrize("locale", RIOT_LOCALES)
async def test_locale_http_status(locale: str, BASE_URL: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/rss/{locale}.xml")
        LocaleFeedValidator.validate_http_200(response)


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.locale
@pytest.mark.parametrize("locale", RIOT_LOCALES)
async def test_locale_xml_wellformed(locale: str, BASE_URL: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/rss/{locale}.xml")
        LocaleFeedValidator.validate_http_200(response)
        feed = feedparser.parse(response.text)
        LocaleFeedValidator.validate_xml_wellformed(feed)


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.locale
@pytest.mark.parametrize("locale", RIOT_LOCALES)
async def test_locale_rss_version(locale: str, BASE_URL: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/rss/{locale}.xml")
        LocaleFeedValidator.validate_http_200(response)
        feed = feedparser.parse(response.text)
        LocaleFeedValidator.validate_xml_wellformed(feed)
        LocaleFeedValidator.validate_rss_version(feed)


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.locale
@pytest.mark.slow
async def test_all_locales_comprehensive(BASE_URL: str) -> None:
    validation_results = {}

    async with httpx.AsyncClient() as client:
        for locale in RIOT_LOCALES:
            results = {}
            try:
                response = await client.get(f"{BASE_URL}/rss/{locale}.xml")
                results["http_200"] = response.status_code == 200
                results["content_type"] = "xml" in response.headers.get("content-type", "").lower()

                feed = feedparser.parse(response.text)
                results["xml_wellformed"] = feed.bozo == 0
                results["rss_version"] = feed.version == "rss20"
                results["non_empty"] = len(feed.entries) > 0

                expected_lang = EXPECTED_LANGUAGES.get(locale, locale.split("-")[0])
                actual_lang = feed.feed.get("language", "")
                results["language_tag"] = actual_lang.lower() == expected_lang.lower()

                guids = [e.id for e in feed.entries if hasattr(e, "id")]
                results["guid_uniqueness"] = len(guids) == len(set(guids)) if guids else True

                results["passed"] = all(results.values())
            except Exception as e:
                for key in [
                    "http_200",
                    "content_type",
                    "xml_wellformed",
                    "rss_version",
                    "non_empty",
                    "language_tag",
                    "guid_uniqueness",
                    "passed",
                ]:
                    results[key] = False
                results["error"] = str(e)  # type: ignore[assignment]

            validation_results[locale] = results

    passed_count = sum(1 for r in validation_results.values() if r.get("passed", False))
    total_count = len(validation_results)

    print()
    print("=" * 70)
    print("MULTI-LOCALE RSS FEED VALIDATION REPORT")
    print("=" * 70)
    print(f"Total: {total_count}, Passed: {passed_count}, Failed: {total_count - passed_count}")
    print("=" * 70)

    for locale, results in validation_results.items():
        status = "PASS" if results.get("passed", False) else "FAIL"
        print(f"{locale}: {status}")
    print("=" * 70)
    print()

    failed_locales = [
        loc for loc, res in validation_results.items() if not res.get("passed", False)
    ]
    if failed_locales:
        pytest.fail(f"Failed: {', '.join(failed_locales)}")


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.locale
async def test_locale_registry_completeness(BASE_URL: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/feeds")
        assert response.status_code == 200
        data = response.json()
        supported_locales = set(data.get("supported_locales", []))
        missing_locales = set(RIOT_LOCALES) - supported_locales
        if missing_locales:
            pytest.fail(f"Missing locales: {', '.join(missing_locales)}")
