from uncertainties.core import AffineScalarFunc
from uncertainties import UFloat
import string
import pymupdf
import random
import re
import os


PATTERNS = {
    'ExIV': {
        'exercise': r'^\d\)\s(.*)\s\(',
        'subexercise': r'^[\s\(]*([a-z])\)'
    },
    'TheoII': {
        'exercise': r"^Aufgabe\s\d\:\s(.*)",
        'subexercise': r'^[\s]*(\([a-z]\))'
    }
}


def extract_exercises_from_pdf(pdf_path, pattern=''):
    exercises = dict()
    current_exercise = None

    if isinstance(pattern, (list, tuple)):
        exercise_pattern, sub_exercise_pattern = pattern
    elif not pattern:
        print('No pattern provided trying first pattern.')
        exercise_pattern, sub_exercise_pattern = list(PATTERNS.values())[0].values()
    else:
        exercise_pattern, sub_exercise_pattern = PATTERNS[pattern]

    exercise_pattern = re.compile(exercise_pattern)
    sub_exercise_pattern = re.compile(sub_exercise_pattern)

    doc = pymupdf.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")

        lines = text.split('\n')

        for line in lines:
            exercise_match = exercise_pattern.match(line.strip())
            sub_exercise_match = sub_exercise_pattern.match(line.strip())

            if exercise_match:
                current_exercise = exercise_match.group(1).strip()
                exercises[current_exercise] = 0

            elif sub_exercise_match and current_exercise:
                exercises[current_exercise] += 1

    return exercises


def insert_exercises_into_tex(exercises: dict, tex_path):
    with open(tex_path, 'r') as file:
        lines = file.readlines()

    doc_start = lines.index('\\begin{document}\n')

    if lines[doc_start + 2] != '\\end{document}\n':
        raise Exception('File not empty!')

    content_string = ''

    def section_str(title, first):
        if first:
            return f"\\section{{{title}}}\n\\setkomafont{{section}}{{\\clearpage}}\n\n"
        return f"\\section{{{title}}}\n\n"

    i = 0
    for title, subexercises in exercises.items():
        content_string += section_str(title, not i) + "\\subsection{}\n\n" * subexercises
        i += 1

    lines.insert(doc_start + 2, content_string)

    with open(tex_path, 'w') as file:
        file.writelines(lines)


def autofill_exercise(U='01'):
    pdf_path = f'ueb/U{U}/uebung{U}.pdf'
    tex_path = f'ueb/U{U}/exercise/U{U}.tex'

    exercises = extract_exercises_from_pdf(pdf_path)
    if not exercises:
        raise Exception('No exercises found in file.')
    insert_exercises_into_tex(exercises, tex_path)
    print(f"TeX file updated at {tex_path}")


def convert_values_to_strings(obj, table_mode=False):
    if isinstance(obj, dict):
        return {key: convert_values_to_strings(value, table_mode) for key, value in obj.items()}

    elif isinstance(obj, (list, tuple)):
        return [convert_values_to_strings(item, table_mode) for item in obj]

    elif isinstance(obj, UFloat) or isinstance(obj, AffineScalarFunc):
        ustr = str(obj)
        if re.search(r'\(?\)', str(obj)):
            num1 = ustr.split('+-')[0].replace('(', '')
            num2 = ustr.split('+-')[-1].split(')')[0]
            exp = ustr.split('+-')[-1].split(')')[-1]
            ustr = f"{num1}+-{num2}{exp}"
        else:
            ustr = f'{obj}'
        if table_mode:
            ustr = f'\\num{{{ustr}}}'
        return ustr

    elif isinstance(obj, float):
        if obj < 1e2 or obj > 1e-2:
            return f'{obj:.3f}'

        if obj < 1e3 or obj > 1e-3:
            return f'{obj:.3e}'

        return f'{obj:0.3f}'

    else:
        return str(obj)


def write_data_table(*args, name=None, collumns='', caption="", vlines=None, table=True, header=None, sider=None, the_turns_have_tabled=False):
    """Writes a data table of the lists given and saves it as a .tex.

    Args:
        name (str, optional): Name used in the label and the filename. If None given, uses four randomized letters instead. Defaults to None.

        collumns (str, optional): Is put into the {cc|cc} option for tex tables. If none given, the vlines will be used to determine the vlines position if given. Defaults to ''.

        caption (str, optional): Your best description of the data you present. Will be added as caption to the table. Defaults to None.

        vlines (list, optional): Is a list defining where in the table vlines should be placed. e.g.: [0,3,4] meaning the tables collumn settings will look like this: {|ccc|c|}. Defaults to None.

        table (boolean, optional): Defines wether table places in a table environment or not. Defaults to True.

        header (str or list, optional): Will be added as a header to the data table. If None given the table will have an empty header. Should be given like this: header="$T_0$ & $h_0$ & \\kappa". Requires no double backslash, space or newline in the end, but tex compatible text.
        Or as a list:
        ["$T_0$", "$h_0$", "\\kappa"]
        If none given, no header and midrule will appear.
        If "numbers" given, the collumns will be enumerated.

        sider (list, optional): Will be added on the left side of the table. Must be given as a list of texable strings.

        the_turns_have_tabled: (boolean, optional): Turns the table`s layout to present the data horizontally. Sider and header are not affected by this. Defaults to False.
    """
    if not name:
        name = "".join(random.choice(string.ascii_letters) for _ in range(4))

    lists = list(args)

    if the_turns_have_tabled:
        lists_new = []
        for i in zip(*lists):
            lists_new += [list(i)]
        lists = lists_new

    if sider:
        lists.insert(0, sider)

    if header == "numbers":
        sider_placeholder = sider
        if sider:
            sider_placeholder = " & "
        header = sider_placeholder + "&".join([str(i) for i in range(1, len(lists)+1)])

    if isinstance(header, str):
        header += " \\\\\n\\midrule\n"

    if isinstance(header, list):
        header = "&".join(header) + " \\\\\n\\midrule\n"

    if collumns:
        n = collumns.__len__() - collumns.count('|')
        if n != len(lists):
            raise Exception('Specified Collumns do not match lists')
        vlines = not n

    if not collumns:
        collumns = len(lists)*"c"
        if sider:
            collumns += "c"

    if vlines:
        temp = (len(lists) + 1)*[""]
        if sider:
            temp += [""]
        for v in vlines:
            temp[v] = "|"
        collumns = "c".join(temp)

    if not os.path.exists("./reports"):
        os.mkdir("./reports")
    if not os.path.exists("./reports/tables"):
        os.mkdir("./reports/tables")
    filename = "./reports/tables/" + name + "_results_data.tex"
    lines = []
    if table:
        lines.append("\\begin{table}[ht!] \n" + "\\centering \n")

    lines.append("\\begin{tabular}{" + collumns + "}\n\\toprule\n")

    if header:
        lines.append(header)

    for i in zip(*lists):
        line_elements = convert_values_to_strings(i, table_mode=True)
        line = " & ".join(line_elements)
        lines.append(line + " \\\\\n")

    lines.append("\\bottomrule\n\\end{tabular} \n")
    if table:
        lines.append("\\caption{" + caption + "}\n\\label{tab:" + name + "} \n\\end{table}")

    with open(filename, "w", encoding='utf-8') as file:
        file.writelines(lines)


def main():
    extract_exercises_from_pdf('', 'ExIV')


if __name__ == "__main__":
    main()
