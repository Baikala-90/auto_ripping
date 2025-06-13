import os
import shutil
import time
import json
from natsort import natsorted  # 추가

def start_auto_transfer(base_folder, folder_names, hotfolder_paths, auto_trigger,
                        log_callback, sort_orders=None, pause_flag=None,
                        folder_stop=None, status_callback=None,
                        folder_pause_flag=None):
    priority_path = os.path.join(base_folder, "folder_priority.json")
    if os.path.exists(priority_path):
        with open(priority_path, "r", encoding="utf-8") as f:
            all_priority = json.load(f)
    else:
        all_priority = folder_names

    priority_list = [f for f in all_priority if f in folder_names]

    file_counts = {}
    total_files = 0
    for folder in priority_list:
        src_path = os.path.join(base_folder, folder)
        jdf_files = [f for f in os.listdir(src_path) if f.lower().endswith(".jdf")]
        pdf_files = [f for f in os.listdir(src_path) if f.lower().endswith(".pdf")]
        common = set(os.path.splitext(f)[0] for f in jdf_files) & set(os.path.splitext(f)[0] for f in pdf_files)
        file_counts[folder] = len(common)
        total_files += file_counts[folder]

    processed = 0
    start_time = time.time()

    for folder in priority_list:
        if status_callback:
            status_callback(folder, "대기", progress=0, remaining=None)

        if folder_stop and pause_flag and not pause_flag.is_set():
            log_callback(f"⏸️ 일시정지됨: {folder}")
            if status_callback:
                status_callback(folder, "일시정지")
            break

        if not auto_trigger.get(folder, False):
            log_callback(f"⏭️ 자동 전송 비활성화: {folder}")
            if status_callback:
                status_callback(folder, "대기")
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
            if status_callback:
                status_callback(folder, "대기")
            continue

        dest_path = hotfolder_paths.get(folder)
        if not dest_path or not os.path.exists(dest_path):
            log_callback(f"❌ 핫폴더 경로 미설정 또는 없음: {folder}")
            if status_callback:
                status_callback(folder, "오류")
            continue

        log_callback(f"📤 전송 시작: {folder} (정렬: {sort_order})")
        if status_callback:
            status_callback(folder, "전송 중", progress=0, remaining=None)

        for idx, base_name in enumerate(common_names, start=1):
            # 개별/전체 일시정지 처리
            while pause_flag and not pause_flag.is_set():
                time.sleep(0.5)
                if folder_pause_flag and not folder_pause_flag.is_set():
                    if status_callback:
                        status_callback(folder, "일시정지")
            while folder_pause_flag and not folder_pause_flag.is_set():
                if status_callback:
                    status_callback(folder, "일시정지")
                time.sleep(0.5)

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
                processed += 1
                if status_callback:
                    remaining = None
                    if processed > 0:
                        remaining = int(((time.time() - start_time) / processed) * (total_files - processed))
                    progress = int(idx / len(common_names) * 100)
                    status_callback(folder, f"전송 중: {base_name}", progress=progress, remaining=remaining)
            except Exception as e:
                log_callback(f"❌ 전송 실패: {base_name} → {str(e)}")
                if status_callback:
                    status_callback(folder, "오류")
                continue

            # 리핑 대기
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
        if status_callback:
            remaining = 0
            if processed > 0:
                remaining = int(((time.time() - start_time) / processed) * (total_files - processed))
            status_callback(folder, "완료", progress=100, remaining=remaining)

    log_callback("🏁 자동 전송 완료.")
