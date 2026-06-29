from benchmark_ocr import ProviderBenchmarkResult, _score


def test_failed_provider_scores_zero():
    result = ProviderBenchmarkResult(
        provider="paddle",
        status="ERROR",
        runtime_seconds=1.0,
        output_file="missing.xlsx",
    )
    assert _score(result, [result]) == 0.0


def test_ok_provider_scores_positive():
    result = ProviderBenchmarkResult(
        provider="easy",
        status="OK",
        runtime_seconds=10.0,
        output_file="out.xlsx",
        rows=100,
        thp_rows=80,
        unknown_names=4,
        review_rows=8,
        valid_rows=72,
        rank_warnings=2,
        server_review_rows=0,
        sheets=4,
    )
    assert _score(result, [result]) > 70
