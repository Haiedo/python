"""
Export utilities for reports (CSV, Excel, PDF)
"""
import io
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def expenses_to_dataframe(expenses):
    """Convert expenses to pandas DataFrame"""
    data = []
    for expense in expenses:
        data.append({
            'ID': expense.id,
            'Date': expense.expense_date.strftime('%Y-%m-%d') if expense.expense_date else '',
            'Description': expense.description,
            'Amount': float(expense.amount),
            'Currency': expense.currency,
            'Category': expense.category.name if expense.category else 'Uncategorized',
            'Paid By': expense.paid_by.full_name or expense.paid_by.username,
            'Split Type': expense.split_type,
            'Status': expense.status,
            'Group': expense.group.name,
            'Created At': expense.created_at.strftime('%Y-%m-%d %H:%M') if expense.created_at else ''
        })

    return pd.DataFrame(data)


def export_expenses_csv(expenses):
    """
    Export expenses to CSV format

    Args:
        expenses: List of Expense objects

    Returns:
        BytesIO object containing CSV data
    """
    df = expenses_to_dataframe(expenses)

    output = io.StringIO()
    df.to_csv(output, index=False)

    # Convert to BytesIO
    bytes_output = io.BytesIO()
    bytes_output.write(output.getvalue().encode('utf-8'))
    bytes_output.seek(0)

    return bytes_output


def export_expenses_excel(expenses):
    """
    Export expenses to Excel format

    Args:
        expenses: List of Expense objects

    Returns:
        BytesIO object containing Excel data
    """
    df = expenses_to_dataframe(expenses)

    output = io.BytesIO()

    # Create Excel writer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Expenses', index=False)

        # Auto-adjust column widths
        worksheet = writer.sheets['Expenses']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).str.len().max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

    output.seek(0)
    return output


def export_expenses_pdf(expenses, group_name=None):
    """
    Export expenses to PDF format

    Args:
        expenses: List of Expense objects
        group_name: Optional group name for the report

    Returns:
        BytesIO object containing PDF data
    """
    buffer = io.BytesIO()

    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=1  # Center
    )

    # Title
    title_text = f"Expense Report{f' - {group_name}' if group_name else ''}"
    title = Paragraph(title_text, title_style)
    elements.append(title)

    # Date
    date_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    date_para = Paragraph(date_text, styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 0.3 * inch))

    # Summary statistics
    if expenses:
        total_amount = sum(float(e.amount) for e in expenses)
        currency = expenses[0].currency if expenses else 'VND'

        summary_data = [
            ['Total Expenses:', len(expenses)],
            ['Total Amount:', f'{total_amount:,.2f} {currency}'],
            ['Status Breakdown:', ''],
            ['  - Pending:', len([e for e in expenses if e.status == 'pending'])],
            ['  - Approved:', len([e for e in expenses if e.status == 'approved'])],
            ['  - Rejected:', len([e for e in expenses if e.status == 'rejected'])]
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 0.5 * inch))

    # Expense table
    if expenses:
        # Table headers
        table_data = [['Date', 'Description', 'Amount', 'Paid By', 'Status']]

        # Table rows
        for expense in expenses:
            table_data.append([
                expense.expense_date.strftime('%Y-%m-%d') if expense.expense_date else '',
                expense.description[:30] + '...' if len(expense.description) > 30 else expense.description,
                f'{float(expense.amount):,.0f}',
                expense.paid_by.username,
                expense.status.upper()
            ])

        # Create table
        expense_table = Table(table_data, colWidths=[1*inch, 2.5*inch, 1*inch, 1.2*inch, 0.8*inch])
        expense_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Body style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))

        elements.append(expense_table)
    else:
        no_data = Paragraph("No expenses to display", styles['Normal'])
        elements.append(no_data)

    # Build PDF
    doc.build(elements)

    buffer.seek(0)
    return buffer


def export_settlements_pdf(settlements_data, group_name):
    """
    Export settlement suggestions to PDF

    Args:
        settlements_data: Settlement data from calculate_settlements
        group_name: Group name

    Returns:
        BytesIO object containing PDF data
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=1
    )

    # Title
    title = Paragraph(f"Settlement Report - {group_name}", title_style)
    elements.append(title)

    # Date
    date_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    elements.append(Paragraph(date_text, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # Settlement table
    settlements = settlements_data.get('settlements', [])

    if settlements:
        table_data = [['From', 'To', 'Amount']]

        for settlement in settlements:
            table_data.append([
                f"User #{settlement['payer_id']}",
                f"User #{settlement['payee_id']}",
                f"{settlement['amount']:,.2f}"
            ])

        settlement_table = Table(table_data, colWidths=[2*inch, 2*inch, 1.5*inch])
        settlement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))

        elements.append(settlement_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Summary
        total_transactions = len(settlements)
        summary_text = f"<b>Total Optimized Transactions:</b> {total_transactions}"
        elements.append(Paragraph(summary_text, styles['Normal']))

        info_text = "These are the minimum number of transactions needed to settle all debts in the group."
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(info_text, styles['Italic']))

    else:
        no_data = Paragraph("All debts are settled! No transactions needed.", styles['Normal'])
        elements.append(no_data)

    doc.build(elements)
    buffer.seek(0)
    return buffer
