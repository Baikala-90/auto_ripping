import os
import pandas as pd
from xml.etree import ElementTree as ET

# ------------------------- 설정 ---------------------------- #
EXCEL_PATH = "2025-06-12.1749685942709.xlsx"
SHEET_NAME = "2025-06-12"
TEMPLATE_FOLDER = "templates"  # 조건별 템플릿 폴더
OUTPUT_FOLDER = "generated_jdfs"  # 생성된 JDF 저장 폴더

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ------------------------- 엑셀 불러오기 ------------------- #
df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

# 열 이름 정리 및 조건 키 생성
df = df[["규격", "코팅", "표지재질", "내지재질", "공정구분", "발주량", "표지파일명", "내지_CS", "내지_IMP", "컬러여부"]].copy()
df.columns = ["size", "binding", "cover_material", "inner_material", "process", "copies", "cover_file", "cs_file", "imp_file", "color"]
df["binding"] = df["binding"].apply(lambda x: "날" if "날개있음" in str(x) else "단")
df["color"] = df["color"].apply(lambda x: "컬러" if pd.notna(x) else "흑백")
df["condition_key"] = df[["size", "binding", "cover_material", "inner_material", "process"]].agg(" ".join, axis=1)

# ------------------------- JDF 생성 함수 ------------------- #
def generate_jdf(template_path, copies):
    with open(template_path, "r", encoding="utf-8") as f:
        jdf_text = f.read()
    return jdf_text.replace("@@COPIES@@", str(copies))

# ------------------------- 메인 실행 ---------------------- #
def generate_all_jdfs():
    for idx, row in df.iterrows():
        key = row["condition_key"]
        copies = row["copies"]

        # 템플릿 파일 경로 추론
        template_file = os.path.join(TEMPLATE_FOLDER, f"{key}.jdf")
        if not os.path.exists(template_file):
            print(f"[SKIP] 조건 '{key}' 에 해당하는 템플릿 없음")
            continue

        # 파일명 설정
        file_targets = []
        if row["process"] == "CS":
            file_targets.append(row["cs_file"])
        elif row["process"] == "IMP":
            file_targets.append(row["imp_file"])
        elif row["process"] == "혼합":
            file_targets += [row["cs_file"], row["imp_file"]]
        file_targets.append(row["cover_file"])  # 표지는 무조건 포함

        for filename in file_targets:
            if not isinstance(filename, str) or not filename.endswith(".pdf"):
                continue
            jdf_result = generate_jdf(template_file, copies)
            output_path = os.path.join(OUTPUT_FOLDER, filename.replace(".pdf", ".jdf"))
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(jdf_result)
            print(f"✅ Generated: {output_path}")

if __name__ == "__main__":
    generate_all_jdfs()
