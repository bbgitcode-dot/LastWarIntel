from pathlib import Path
import cv2


def draw_debug_boxes(image, ocr_results, output_file):
    debug = image.copy()

    for box, text, confidence in ocr_results:

        pts = [(int(x), int(y)) for x, y in box]

        for i in range(4):
            cv2.line(
                debug,
                pts[i],
                pts[(i + 1) % 4],
                (0, 255, 0),
                2
            )

        cv2.putText(
            debug,
            f"{confidence:.2f}",
            (pts[0][0], pts[0][1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 0, 0),
            1,
            cv2.LINE_AA
        )

    output = Path(output_file)
    output.parent.mkdir(exist_ok=True)

    cv2.imwrite(str(output), debug)