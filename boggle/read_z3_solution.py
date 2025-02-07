import fileinput
import re


def main():
    lines = [line.strip() for line in fileinput.input()]

    if lines[0] != "sat":
        print(f"not sat! {lines[0]}")
        return

    cells = {}

    i = 2
    while i < len(lines):
        line = lines[i]
        if "Int" in line:
            i += 2
            continue
        if "Bool" not in line:
            i += 1
            continue
        m = re.search(r"define-fun ([a-z])(\d) \(\) Bool", line)
        assert m, line
        (letter, cell_str) = m.groups()
        nextline = lines[i + 1]
        if "true" in nextline:
            cell = int(cell_str)
            cells[cell] = letter

        i += 2

    print(" ".join(cells[i] for i in range(len(cells))))


if __name__ == "__main__":
    main()
