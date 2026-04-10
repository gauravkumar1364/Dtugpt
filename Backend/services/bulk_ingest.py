import os
from main import process_pdf  # reuse your function

BASE_FOLDER = "download"   # folder from gdown


def process_all_subjects():

    total_files = 0

    for subject in os.listdir(BASE_FOLDER):

        subject_path = os.path.join(BASE_FOLDER, subject)

        if not os.path.isdir(subject_path):
            continue

        print(f"\n📘 SUBJECT: {subject}")

        for file in os.listdir(subject_path):

            if not file.lower().endswith(".pdf"):
                continue

            file_path = os.path.join(subject_path, file)

            year = file.replace(".pdf", "")

            print(f"   📄 Processing: {file}")

            try:
                process_pdf(file_path, subject.lower(), year)
                total_files += 1

            except Exception as e:
                print(f"   ❌ Error: {e}")

    print(f"\n✅ DONE: Processed {total_files} files")


if __name__ == "__main__":
    process_all_subjects()