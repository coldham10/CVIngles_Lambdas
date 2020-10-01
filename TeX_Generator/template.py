preamble = "\\documentclass[11pt,a4paper,sans]{{moderncv}}\n\\moderncvstyle{{{style}}}\n\\moderncvcolor{{{color}}}\n\\usepackage[scale=0.8]{{geometry}}\n\\name{{{fname}}}{{{lname}}}\n{personal}\n\n"


class personal:
    phone = "\\phone[{type}]{{{val}}}\n"
    website = "\\homepage{{{val}}} \n"
    email = "\\email{{{email}}} \n"
    address = "\\address{{{line_1}}}{{{line_2}}}{{{country}}}\n"
    social = "\\social[{type}]{{{val}}}\n"
    extra = "\\extrainfo{{{val}}} \n"
    picture = "\\photo[64pt][0.4pt]{{{picture}}}\n"


body = "\\begin{{document}}\n\n\\makecvtitle\n\n{content}\n\\clearpage\n\n\\end{{document}}\n"

section = "\\section{{{name}}}\n{content}\n\n"

degree = "\\cventry{{{start}--{end}}}{{{title}}}{{{school}}}{{{city}}}{{\\textit{{{grade}}}}}{{{desc}}}\n"
job = "\\cventry{{{start}--{end}}}{{{title}}}{{{employer}}}{{{city}}}{{}}{{{desc}\\newline{{}}\n{achievements}}}\n"
achievements = "Principal Functions and Responsibilities:\n\\begin{{itemize}}\n{list}\\end{{itemize}}\n"
achievement = "\\item {desc}\n"
language = "\\cvitem{{{name}}}{{{ability}}}\n"
interest = "\\cvitem{{{name}}}{{{desc}}}\n"
thesis = "\\section{{Master's Thesis}}\n\\cvitem{{Title}}{{\\emph{{{name}}}}}\n\\cvitem{{Supervisors}}{{{supervisors}}}\n\\cvitem{{Description}}{{{desc}}}\n"
custom = "\\cvitem{{{name}}}{{{desc}}}\n"
custom_comment = "\\cvitemwithcomment{{{name}}}{{{desc}}}{{{comment}}}\n"

lang_level_dict = {
    "x0": "Basic",
    "x1": "Conversational",
    "x2": "Fluent",
    "x3": "Native speaker",
    "a1": "CEFR Level A1 (Beginner)",
    "a2": "CEFR Level A2 (Elementary)",
    "b1": "CEFR Level B1 (Intermediate)",
    "v2": "CEFR Level B2 (Independent)",
    "c1": "CEFR Level C1 (Working proficiency)",
    "c2": "CEFR Level C2 (Full proficiency)",
    "i0": "ILR Level 0 (Basic)",
    "i1": "ILR Level 1 (Elementary proficiency)",
    "i2": "ILR Level 2 (Limited working proficiency)",
    "i3": "ILR Level 3 (Professional working proficiency)",
    "i4": "ILR Level 4 (Full professional proficiency)",
    "i5": "ILR Level 5 (Bilingual proficiency)",
}
