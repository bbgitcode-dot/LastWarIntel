from ocr.paddleocr_provider import _extract_items


class FakePaddleResult:
    @property
    def json(self):
        return {
            "res": {
                "rec_texts": ["Warzone #549", "[SW3] Bierbaer"],
                "rec_scores": [0.98, 0.87],
                "rec_polys": [
                    [[1, 2], [3, 2], [3, 4], [1, 4]],
                    [[5, 6], [7, 6], [7, 8], [5, 8]],
                ],
            }
        }


def test_extract_items_supports_paddle_v3_result_objects():
    items = list(_extract_items([FakePaddleResult()]))

    assert len(items) == 2
    assert items[0][1] == "Warzone #549"
    assert items[0][2] == 0.98
    assert items[1][1] == "[SW3] Bierbaer"
