from openpyxl import Workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment
import yaml

def generate_summary(change):
    summary = []

    def format_yaml(value):
        if isinstance(value, (dict, list)):
            return yaml.dump(value, default_flow_style=False, sort_keys=False).strip()
        return value

    def format_change(path, value, change_type):
        if isinstance(value, dict):
            # each key-value pair in the dictionary is with a newline and a dash
            formatted_value = "\n".join([f"- {k}: {format_yaml(v)}" for k, v in value.items()])
        else:
            formatted_value = f"- {format_yaml(value)}"

        if path == 'Root':
            return f"{change_type}:\n{formatted_value}"
        else:
            return f"{change_type}:\n{path}\n{formatted_value}"

    def compare_dicts(left, right, path=''):
        keys = set(left.keys()).union(right.keys())
        for key in keys:
            left_value = left.get(key)
            right_value = right.get(key)
            new_path = f"{path}.{key}" if path else key

            if left_value is None:
                summary.append(format_change(new_path, right_value, "Added"))
            elif right_value is None:
                summary.append(format_change(new_path, left_value, "Removed"))
            elif isinstance(left_value, dict) and isinstance(right_value, dict):
                compare_dicts(left_value, right_value, new_path)
            elif isinstance(left_value, list) and isinstance(right_value, list):
                compare_lists(left_value, right_value, new_path)
            elif left_value != right_value:
                if right_value is None:
                    summary.append(format_change(new_path, left_value, "Removed"))
                else:
                    summary.append(format_change(new_path, right_value, "Added"))

    def compare_lists(left, right, path):
        added_items = [item for item in right if item not in left]
        removed_items = [item for item in left if item not in right]

        for item in added_items:
            summary.append(format_change(path, item, "Added"))
        for item in removed_items:
            summary.append(format_change(path, item, "Removed"))

    # root level differences
    if isinstance(change['left'], dict) and isinstance(change['right'], dict):
        compare_dicts(change['left'], change['right'])
    elif isinstance(change['left'], list) and isinstance(change['right'], list):
        compare_lists(change['left'], change['right'], '')
    else:
        compare_dicts({'Root': change['left']}, {'Root': change['right']}, '')

    final_summary = '\n'.join(summary)
    return final_summary


def generate_excel_report(all_differences, xlsx_file_path):
    wb = Workbook()
    ws = wb.active
    headers = ['Section', 'Path', 'PolishApi', 'Santander', 'Summary']
    ws.append(headers)
    ws.auto_filter.ref = ws.dimensions
    for section, diffs in all_differences.items():
        for path, change in diffs.items():
            ws.append([
                section,
                path,
                change.get('left', ''),
                change.get('right', ''),
                change.get('summary', '')
            ])

    # Change header colors
    header_colors = {
        'A': 'D3D3D3',  # Light gray
        'B': 'DDA0DD',  # Light purple
        'C': '90EE90',  # Light green
        'D': 'FF6347',  # Darker red for Santander
        'E': 'F0F0F0',  # Very light gray for Summary
    }

    for column, color in header_colors.items():
        ws[column + '1'].fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    section_colors = {
        'PIS': 'FFF0E0', 'CAF': 'E0FFF0', 'AIS': 'E0E0FF', 'AS': 'FFE0E0', 'Definitions': 'FFF0FF'
    }
    for row in ws.iter_rows(min_row=2, max_col=1, values_only=False):
        section = row[0].value
        if section in section_colors:
            row[0].fill = PatternFill(start_color=section_colors[section], end_color=section_colors[section], fill_type="solid")

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    for row in ws.iter_rows():
        for cell in row:
            cell.border = thin_border

    column_widths = {'B': 60, 'C': 45, 'D': 35, 'E': 35}
    for column, width in column_widths.items():
        ws.column_dimensions[column].width = width

    ws.delete_cols(6)

    top_left_alignment = Alignment(horizontal='left', vertical='top',wrap_text=True)
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = top_left_alignment
            new_height = max(cell.value.count('\n') + 1, 1) * 15
            if ws.row_dimensions[cell.row].height is None or \
               ws.row_dimensions[cell.row].height < new_height:
                ws.row_dimensions[cell.row].height = new_height

    ws.freeze_panes = 'A2'
    xlsx_file_path_temp = xlsx_file_path
    wb.save(xlsx_file_path_temp)