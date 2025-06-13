import os
import json
import pandas as pd
import re
import math  # 추가됨

# 경로 설정
UPLOAD_FOLDER = "D:/개발/cannon_auto/uploads"
CONFIG_FILE = "D:/개발/cannon_auto/config.json"
OUTPUT_ROOT = "D:/개발/cannon_auto/outputs"
COVER_FOLDER = os.path.join(OUTPUT_ROOT, "COVER")
CS_FOLDER = os.path.join(OUTPUT_ROOT, "CS")
IMP_FOLDER = os.path.join(OUTPUT_ROOT, "IMP")

# 출력 폴더 생성
os.makedirs(COVER_FOLDER, exist_ok=True)
os.makedirs(CS_FOLDER, exist_ok=True)
os.makedirs(IMP_FOLDER, exist_ok=True)

# 수량 추출
def extract_copies(text):
    if pd.isna(text):
        return None
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None

# 파일명에서 내지 재질 추출
def extract_paper_from_filename(filename):
    for paper in ["미100", "미80", "이80", "백100", "백80"]:
        if paper in str(filename):
            return paper
    return "미80"

# 제본 변환
def get_binding(text):
    return "단" if "단" in str(text) else "날"

# 표지재질 변환
def get_cover_code(text):
    if "대중" in str(text): return "스무"
    if "광택" in str(text): return "스유"
    return "아무"

# config 로딩
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# JDF 생성
def generate_jdf(template_path, copies, output_path):
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("@@COPIES@@", str(copies))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    config = load_config(CONFIG_FILE)

    # 최신 엑셀 선택
    excel_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".xlsx")]
    if not excel_files:
        print("❌ 엑셀 파일이 없습니다.")
        return
    excel_path = os.path.join(UPLOAD_FOLDER, sorted(excel_files)[-1])
    df = pd.read_excel(excel_path)

    for _, row in df.iterrows():
        fmt = str(row.get("규격")).strip()
        bind = get_binding(row.get("폴더"))
        cover = get_cover_code(row.get("표지재질"))
        paper = extract_paper_from_filename(row.get("표지파일명"))
        qty = extract_copies(row.get("발주량"))
        process = str(row.get("공정구분")).strip().lower()
        cs_file = row.get("내지_CS")
        imp_file = row.get("내지_IMP")
        base_name = os.path.splitext(str(row.get("표지파일명")))[0]

        if not all([fmt, bind, cover, paper, qty]):
            continue

        # COVER는 무조건 생성
        key_cover = f"{fmt}_{bind}_{cover}_{paper}_COVER"
        if key_cover in config:
            path = config[key_cover]["file"]
            out_path = os.path.join(COVER_FOLDER, base_name + ".jdf")
            generate_jdf(path, qty, out_path)
            print(f"✅ COVER 생성: {out_path}")
        else:
            print(f"⚠️ COVER 템플릿 없음: {key_cover}")

        # CS / IMP 생성 조건
        is_small = fmt in ["A5", "46판"]

        if is_small:
            if process == "cs" and pd.notna(cs_file):
                key_cs = f"{fmt}_{bind}_{cover}_{paper}_CS"
                if key_cs in config:
                    out_path = os.path.join(CS_FOLDER, os.path.splitext(cs_file)[0] + ".jdf")
                    generate_jdf(config[key_cs]["file"], 1, out_path)
                    print(f"✅ CS 생성: {out_path}")
                else:
                    print(f"⚠️ CS 템플릿 없음: {key_cs}")

            elif process == "imp" and pd.notna(imp_file):
                key_imp = f"{fmt}_{bind}_{cover}_{paper}_IMP"
                if key_imp in config:
                    imp_qty = math.ceil((qty - 1) / 2)  # 🔄 변경된 부분 (올림 처리)
                    out_path = os.path.join(IMP_FOLDER, os.path.splitext(imp_file)[0] + ".jdf")
                    generate_jdf(config[key_imp]["file"], imp_qty, out_path)
                    print(f"✅ IMP 생성: {out_path}")
                else:
                    print(f"⚠️ IMP 템플릿 없음: {key_imp}")

            elif process == "혼합":
                # CS
                if pd.notna(cs_file):
                    key_cs = f"{fmt}_{bind}_{cover}_{paper}_CS"
                    if key_cs in config:
                        out_path = os.path.join(CS_FOLDER, os.path.splitext(cs_file)[0] + ".jdf")
                        generate_jdf(config[key_cs]["file"], 1, out_path)
                        print(f"✅ CS 생성: {out_path}")
                    else:
                        print(f"⚠️ CS 템플릿 없음: {key_cs}")
                # IMP
                if pd.notna(imp_file):
                    key_imp = f"{fmt}_{bind}_{cover}_{paper}_IMP"
                    if key_imp in config:
                        imp_qty = math.ceil((qty - 1) / 2)  # 🔄 변경된 부분 (올림 처리)
                        out_path = os.path.join(IMP_FOLDER, os.path.splitext(imp_file)[0] + ".jdf")
                        generate_jdf(config[key_imp]["file"], imp_qty, out_path)
                        print(f"✅ IMP 생성: {out_path}")
                    else:
                        print(f"⚠️ IMP 템플릿 없음: {key_imp}")

        else:
            # A4, B5 (1UP)는 무조건 IMP만 생성, 수량 = qty
            if pd.notna(imp_file):
                key_imp = f"{fmt}_{bind}_{cover}_{paper}_IMP"
                if key_imp in config:
                    out_path = os.path.join(IMP_FOLDER, os.path.splitext(imp_file)[0] + ".jdf")
                    generate_jdf(config[key_imp]["file"], qty, out_path)
                    print(f"✅ IMP 생성: {out_path}")
                else:
                    print(f"⚠️ IMP 템플릿 없음: {key_imp}")

if __name__ == "__main__":
    main()
