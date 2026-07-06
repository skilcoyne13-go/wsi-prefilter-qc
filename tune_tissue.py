import sys
import cv2
from wsi_qc.loader import load_slide
from wsi_qc.checks.tissue_finder import segment_fragments, _exclude_label_band


def _overlay(rgb, mask):
    out = rgb.copy()
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, contours, -1, (0, 255, 0), 3)
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: python tune_tissue.py <path to slide>")
        return
    s = load_slide(sys.argv[1])
    print("is_composite_macro:", s.is_composite_macro)
    print("macro size:", s.macro_image.shape, "thumb size:", s.thumbnail_image.shape)
    if s.is_composite_macro:
        glass = _exclude_label_band(s.macro_image)
    else:
        glass = s.macro_image
    mf, mmask = segment_fragments(glass)
    tf, tmask = segment_fragments(s.thumbnail_image)
    print("macro fragments:", len(mf), mf)
    print("thumb fragments:", len(tf), tf)
    cv2.imwrite("tune_macro.png", cv2.cvtColor(_overlay(glass, mmask), cv2.COLOR_RGB2BGR))
    cv2.imwrite("tune_thumb.png", cv2.cvtColor(_overlay(s.thumbnail_image, tmask), cv2.COLOR_RGB2BGR))
    cv2.imwrite("raw_macro.png", cv2.cvtColor(s.macro_image, cv2.COLOR_RGB2BGR))
    cv2.imwrite("raw_thumb.png", cv2.cvtColor(s.thumbnail_image, cv2.COLOR_RGB2BGR))
    print("wrote 4 PNGs")


if __name__ == "__main__":
    main()