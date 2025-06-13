import os
import shutil
import time
import json
from natsort import natsorted  # 추가

def start_auto_transfer(base_folder, folder_names, hotfolder_paths, auto_trigger, log_callback, sort_orders=None, pause_flag=None, folder_stop=None):
    priority_path = os.path.join(base_folder, "folder_priority.json")
    if os.path.exists(priority_path):
        with open(priority_path, "r", encoding="utf-8") as f:
            all_priority = json.load(f)
    else:
        all_priority = folder_names

    priority_list = [f for f in all_priority if f in folder_names]

    for folder in priority_list:
        if folder_stop and pause_flag and not pause_flag.is_set():
            log_callback(f"⏸️ 일시정지됨: {folder}")
            break

        if not auto_trigger.get(folder, False):
            log_callback(f"⏭️ 자동 전송 비활성화: {folder}")
            continue

        src_path = os.path.join(base_folder, folder)
        jdf_files = [f for f in os.listdir(src_path) if f.lower().endswith(".jdf")]
        pdf_files = [f for f in os.listdir(src_path) if f.lower().endswith(".pdf")]

        jdf_names = set(os.path.splitext(f)[0] for f in jdf_files)
        pdf_names = set(os.path.splitext(f)[0] for f in pdf_files)
        common_names = list(jdf_names & pdf_names)

        sort_order = sort_orders.get(folder, "오름차순") if sort_orders else "오름차순"
        reverse = sort_order == "내림차순"
        common_names = natsorted(common_names, reverse=reverse)  # 자연 정렬 적용

        if not common_names:
            log_callback(f"⏸ 일치하는 JDF+PDF 쌍 없음: {folder}")
            continue

        dest_path = hotfolder_paths.get(folder)
        if not dest_path or not os.path.exists(dest_path):
            log_callback(f"❌ 핫폴더 경로 미설정 또는 없음: {folder}")
            continue

        log_callback(f"📤 전송 시작: {folder} (정렬: {sort_order})")

        for base_name in common_names:
            jdf = base_name + ".jdf"
            pdf = base_name + ".pdf"

            jdf_src = os.path.join(src_path, jdf)
            pdf_src = os.path.join(src_path, pdf)
            jdf_dest = os.path.join(dest_path, jdf)
            pdf_dest = os.path.join(dest_path, pdf)

            try:
                shutil.copy2(jdf_src, jdf_dest)
                shutil.copy2(pdf_src, pdf_dest)
                log_callback(f"✅ 전송됨: {jdf}, {pdf}")
            except Exception as e:
                log_callback(f"❌ 전송 실패: {base_name} → {str(e)}")
                continue

            wait_time = 60
            interval = 2
            elapsed = 0
            while os.path.exists(pdf_dest) and elapsed < wait_time:
                time.sleep(interval)
                elapsed += interval

            if os.path.exists(pdf_dest):
                log_callback(f"⚠️ 리핑 대기 초과: {pdf}")
            else:
                try:
                    if os.path.exists(jdf_dest):
                        os.remove(jdf_dest)
                        log_callback(f"🗑 JDF 삭제 (핫폴더): {jdf}")
                except Exception as e:
                    log_callback(f"⚠️ JDF 삭제 실패: {jdf} → {str(e)}")

        log_callback(f"✅ 폴더 완료: {folder}")

    log_callback("🏁 자동 전송 완료.")
