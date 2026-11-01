from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)


OUT = Path(r"C:\VINAY\roleradar\output\pdf\RoleRadar_Project_Diary.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)
PAGE_W, PAGE_H = landscape(A4)
INK = colors.HexColor("#1D2A3A")
BLUE = colors.HexColor("#244B70")
PALE = colors.HexColor("#EAF0F5")
GRID = colors.HexColor("#9AA8B5")


class DiaryDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(filename, pagesize=landscape(A4),
                         leftMargin=17*mm, rightMargin=17*mm,
                         topMargin=15*mm, bottomMargin=17*mm,
                         title="RoleRadar Project Diary")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      id="main", leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="diary", frames=[frame], onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#596979"))
            canvas.drawString(17*mm, 9*mm, "RoleRadar | Project Diary")
            canvas.drawRightString(PAGE_W - 17*mm, 9*mm, f"Page {doc.page}")
        canvas.restoreState()


title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18,
                       leading=22, textColor=INK, alignment=TA_CENTER, spaceAfter=5)
sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9,
                     leading=13, textColor=colors.HexColor("#4F5D6B"), alignment=TA_CENTER)
heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12,
                         leading=16, textColor=INK, alignment=TA_CENTER, spaceAfter=10)
cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5,
                      leading=11.5, textColor=INK, alignment=TA_LEFT)
cell_bold = ParagraphStyle("cellbold", parent=cell, fontName="Helvetica-Bold")
header = ParagraphStyle("header", parent=cell_bold, textColor=colors.white,
                        fontSize=8, leading=9.5)
small = ParagraphStyle("small", fontName="Helvetica", fontSize=8,
                       leading=11, textColor=INK)


def P(text, style=cell):
    return Paragraph(text, style)


def cover():
    story = [Spacer(1, 2*mm),
             P("PROJECT DIARY", title),
             P("RoleRadar Career Support and Job Search Platform", sub),
             Spacer(1, 5*mm), P("Project Details", heading)]
    rows = [
        [P("Institution / Department", cell_bold), P("____________________________________________________________", cell)],
        [P("Title of the Project", cell_bold), P("RoleRadar: Career Support and Job Search Platform", cell_bold)],
        [P("Project Associates", cell_bold), P("1.  ________________________________________________<br/><br/>2.  ________________________________________________<br/><br/>3.  ________________________________________________<br/><br/>4.  ________________________________________________", cell)],
        [P("Project Guide Name", cell_bold), P("____________________________________________________________", cell)],
        [P("Project Period", cell_bold), P("20 August 2026 to 22 October 2026 (milestones recorded in the repository)", cell)],
    ]
    t = Table(rows, colWidths=[52*mm, 194*mm], rowHeights=[12*mm, 16*mm, 48*mm, 16*mm, 16*mm])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.7, GRID),
        ("BACKGROUND", (0,0), (0,-1), PALE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 10), ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story += [t, Spacer(1, 8*mm)]
    signatures = Table([
        [P("Project Guide", cell_bold), P("Project Coordinators", cell_bold), P("Program Coordinator", cell_bold)],
        [P("Signature: ____________________<br/>Date: ________________________", small),
         P("Signature: ____________________<br/>Date: ________________________", small),
         P("Signature: ____________________<br/>Date: ________________________", small)],
    ], colWidths=[82*mm, 82*mm, 82*mm])
    signatures.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(signatures)
    return story


entries = [
    ("20-22 Aug 2026", "Created the initial RoleRadar application structure and established the first working project baseline.", "Completed"),
    ("24-29 Aug 2026", "Expanded resume tailoring and export, added Career Copilot workflows, and improved job filtering and resume review.", "Completed"),
    ("31 Aug-05 Sep 2026", "Built the end-to-end ATS tailoring pipeline, including resume layout analysis, semantic reconstruction, evidence mapping, and opportunity intelligence.", "Completed"),
    ("07-12 Sep 2026", "Refined career-skill intelligence and student workflows; addressed performance and reliability issues in the application.", "Completed"),
    ("14-19 Sep 2026", "Hardened production configuration and frontend serving, and consolidated development work before the next integration stage.", "Completed"),
    ("20-26 Sep 2026", "Resolved integration conflicts and dependency issues, then stabilized the tailoring pipeline, role taxonomy, and related checks.", "Completed"),
    ("27 Sep-03 Oct 2026", "Added compensation extraction and job-source updates, then improved the job experience and RoleRadar interface.", "Completed"),
    ("05-10 Oct 2026", "Improved career-preparation and application workflows and polished the user interface, score explanation, and navigation.", "Completed"),
    ("12-17 Oct 2026", "Strengthened resume-tailoring validation and export workflows and made additional interface improvements.", "Completed"),
    ("19-22 Oct 2026", "Fixed job-skill preservation when canonical extraction is empty and corrected Truth Guard fragment scanning against source resume evidence.", "Completed"),
]


def diary_page(batch, page_index):
    story = [Spacer(1, 1*mm), P("Project Diary", title),
             P("Weekly development milestones", sub), Spacer(1, 7*mm)]
    data = [[P("Sl. No.", header), P("Period", header), P("Tasks Assigned", header),
             P("Status of Task Assigned", header), P("Guide Signature with Date", header)]]
    for idx, (period, task, status) in enumerate(batch, start=page_index*5+1):
        data.append([P(str(idx), cell), P(period, cell), P(task, cell), P(status, cell), P("<br/><br/><br/>", cell)])
    widths = [15*mm, 36*mm, 121*mm, 36*mm, 38*mm]
    tbl = Table(data, colWidths=widths, rowHeights=[11*mm] + [21*mm]*len(batch), repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.6, GRID),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (1,-1), "CENTER"),
        ("ALIGN", (3,1), (3,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story += [tbl, Spacer(1, 5*mm)]
    signs = Table([[P("Project Coordinators", cell_bold), P("Program Coordinator", cell_bold)],
                   [P("Signature: ____________________<br/>Date: ________________________", small),
                    P("Signature: ____________________<br/>Date: ________________________", small)]],
                  colWidths=[123*mm, 123*mm])
    signs.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(signs)
    return story


story = cover() + [PageBreak()]
for page_no, start in enumerate((0, 5)):
    if page_no:
        story.append(PageBreak())
    story += diary_page(entries[start:start+5], page_no)

doc = DiaryDoc(str(OUT))
doc.build(story)
print(OUT)
