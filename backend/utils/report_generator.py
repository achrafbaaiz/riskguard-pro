"""PDF report generation with ReportLab."""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
RISK_COLORS = ["#10b981", "#f59e0b", "#f97316", "#ef4444"]
RISK_LABELS = ["Faible", "Modéré", "Élevé", "Critique"]


def generate_report(analysis: dict) -> str:
    """Generate a PDF report for an analysis. Returns file path."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    filename = f"report_{analysis['id']}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22, textColor=HexColor("#1f2937"))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=12, textColor=HexColor("#6b7280"))
    
    elements = []
    
    # Header
    elements.append(Paragraph("RiskGuard Pro", title_style))
    elements.append(Paragraph("Rapport d'Analyse de Risque", subtitle_style))
    elements.append(Spacer(1, 1*cm))
    
    # Company info
    elements.append(Paragraph(f"<b>Entreprise:</b> {analysis['company_name']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Secteur:</b> {analysis.get('sector', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Date d'analyse:</b> {analysis['created_at'][:10]}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Risk score
    risk_color = RISK_COLORS[analysis['risk_class']]
    score_style = ParagraphStyle('Score', parent=styles['Normal'], fontSize=16, alignment=TA_CENTER)
    elements.append(Paragraph(
        f"<b>Score de risque: </b><font color='{risk_color}'>{analysis['risk_score']:.1f}/100 — {analysis['risk_label']}</font>",
        score_style
    ))
    elements.append(Spacer(1, 0.5*cm))
    
    # Probabilities table
    prob_data = [["Classe", "Probabilité"]]
    for i, (label, prob) in enumerate(zip(RISK_LABELS, analysis['probabilities'])):
        prob_data.append([label, f"{prob*100:.1f}%"])
    
    prob_table = Table(prob_data, colWidths=[6*cm, 4*cm])
    prob_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor("#f3f4f6")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    elements.append(prob_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Recommendations
    elements.append(Paragraph("<b>Recommandations:</b>", styles['Normal']))
    for rec in analysis.get('recommendations', []):
        elements.append(Paragraph(f"• {rec}", styles['Normal']))
    
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        f"<i>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — RiskGuard Pro</i>",
        subtitle_style
    ))
    
    doc.build(elements)
    return filepath
