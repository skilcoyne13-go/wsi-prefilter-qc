import numpy as np
from wsi_qc.models import SlideInputs, SlideMetadata
from wsi_qc.checks.duplicate_label import DuplicateLabelCheck


def barcode_label(start):
    img = np.full((120, 300, 3), 245, dtype=np.uint8)
    for i in range(start, 280, 12):
        img[20:60, i:i + 4] = 20
    return img


def make(name, barcode, label):
    meta = SlideMetadata(patient_id="P", case_id=barcode, barcode_string=barcode)
    return SlideInputs(wsi_path=name, macro_image=label, thumbnail_image=label,
                       label_image=label, metadata=meta)


def main():
    check = DuplicateLabelCheck()
    shared = barcode_label(20)
    distinct = np.full((120, 300, 3), 245, dtype=np.uint8)
    distinct[30:90, 40:260] = 30

    slides = [
        make("slide_A.svs", "SK26-493035_A_HE", shared),
        make("slide_B.svs", "SK26-493035_A_HE", shared),     # same case+partset+stain, near-identical -> freeze
        make("slide_C.svs", "SK26-493035_A_ABPAS", shared),  # same case+partset, different stain -> distinct, never flag
        make("slide_D.svs", "SK26-493035_B_HE", shared),     # same case, different partset -> normal, never flag
        make("slide_E.svs", "SK26-493036_A_HE", shared),     # different case, near-identical -> warning
        make("slide_F.svs", "SK26-493036_B_HE", distinct),   # different label -> fine
    ]
    for s in slides:
        f = check.run(s, None)
        print(str(s.wsi_path).ljust(14), "PASS" if f.passed else "FLAG",
              "(" + f.severity.value + ") ::", f.message)


if __name__ == "__main__":
    main()