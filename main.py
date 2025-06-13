import os
import json
import pandas as pd
import re
import math
import shutil

# 경로 설정
UPLOAD_FOLDER = "D:/개발/cannon_auto/uploads"
CONFIG_FILE = "D:/개발/cannon_auto/config.json"
OUTPUT_ROOT = "C:/제작폴더/@자동립핑"  # 분류 저장 경로
TEMP_FOLDER = "D:/개발/cannon_auto/temp_jdf"

# 임시 저장 폴더 생성
os.makedirs(TEMP_FOLDER, exist_ok=True)

# 수량 추출
def extract_copies(text):
    if pd.isna(text):
        return None
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None

# 내지 재질 추출
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

# 흑백/컬러 구분
def get_color(paper):
    return "컬" if paper in ["백100", "백80"] else "흑"

# 규격 정규화
def normalize_format(fmt):
    return fmt.replace(" ", "").replace("판", "").upper()

# 폴더 이름 계산
def get_destination_folder(fmt, paper, bind):
    fmt = normalize_format(fmt)
    color = get_color(paper)
    if fmt == "A4":
        bind = "단"  # A4는 무조건 단
    return f"면지 결과파일_{color}{bind}{fmt}"

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

        # COVER 생성
        key_cover = f"{fmt}_{bind}_{cover}_{paper}_COVER"
        if key_cover in config:
            path = config[key_cover]["file"]
            dest_folder = os.path.join(OUTPUT_ROOT, "표지검사_정상")
            os.makedirs(dest_folder, exist_ok=True)
            out_path = os.path.join(dest_folder, base_name + ".jdf")
            generate_jdf(path, qty, out_path)
            print(f"✅ COVER → 표지검사_정상: {out_path}")
        else:
            print(f"⚠️ COVER 템플릿 없음: {key_cover}")

        # 소형 판형 여부 확인
        is_small = fmt in ["A5", "46", "46판"]

        # CS
        if process in ["cs", "혼합"] and pd.notna(cs_file):
            key_cs = f"{fmt}_{bind}_{cover}_{paper}_CS"
            if key_cs in config:
                temp_jdf_path = os.path.join(TEMP_FOLDER, os.path.splitext(cs_file)[0] + ".jdf")
                generate_jdf(config[key_cs]["file"], 1, temp_jdf_path)

                folder_name = get_destination_folder(fmt, paper, bind)
                dest_path = os.path.join(OUTPUT_ROOT, folder_name, os.path.basename(temp_jdf_path))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy(temp_jdf_path, dest_path)
                print(f"✅ CS → {folder_name}: {dest_path}")
            else:
                print(f"⚠️ CS 템플릿 없음: {key_cs}")

        # IMP
        if process in ["imp", "혼합"] and pd.notna(imp_file):
            key_imp = f"{fmt}_{bind}_{cover}_{paper}_IMP"
            if key_imp in config:
                imp_qty = math.ceil((qty - 1) / 2) if is_small else qty
                temp_jdf_path = os.path.join(TEMP_FOLDER, os.path.splitext(imp_file)[0] + ".jdf")
                generate_jdf(config[key_imp]["file"], imp_qty, temp_jdf_path)

                folder_name = get_destination_folder(fmt, paper, bind)
                dest_path = os.path.join(OUTPUT_ROOT, folder_name, os.path.basename(temp_jdf_path))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy(temp_jdf_path, dest_path)
                print(f"✅ IMP → {folder_name}: {dest_path}")
            else:
                print(f"⚠️ IMP 템플릿 없음: {key_imp}")

if __name__ == "__main__":
    main()
