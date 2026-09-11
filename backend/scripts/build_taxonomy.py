import os
import json
import openpyxl

def build():
    excel_path = r"D:\My_docs\IMP_Files\Documentation\Erode Collectorate\Confidential\AI Tools\GDP\Monday_GDP_Petitions\Monday GDP Petitions\CM Helpline Grievances Mapping.xlsx"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb["Main Sheet"]

    taxonomy = []
    current_dept = ""

    for r in range(2, sheet.max_row + 1):
        dept_val = sheet.cell(r, 1).value
        if dept_val and str(dept_val).strip():
            current_dept = str(dept_val).strip()
        
        g_type = sheet.cell(r, 2).value
        g_sub = sheet.cell(r, 3).value
        sub_dept = sheet.cell(r, 4).value
        resp_off = sheet.cell(r, 5).value

        if g_type or g_sub:
            taxonomy.append({
                "department": current_dept,
                "grievance_type": str(g_type or "").strip(),
                "grievance_sub_type": str(g_sub or "").strip(),
                "sub_department": str(sub_dept or "").strip(),
                "responsible_officer": str(resp_off or "").strip()
            })

    os.makedirs("data", exist_ok=True)
    out_path = os.path.join("data", "cm_helpline_taxonomy.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, ensure_ascii=False, indent=2)

    unique_depts = len(set(t["department"] for t in taxonomy))
    print(f"Parsed {len(taxonomy)} taxonomy records across {unique_depts} departments!")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    build()
