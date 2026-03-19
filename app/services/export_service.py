import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from fastapi import HTTPException, status

from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction


async def generate_transaction_pdf(current_user: User, db: AsyncSession) -> bytes:
    # fetch wallet
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    # fetch all transactions for this wallet
    result = await db.execute(
        select(Transaction).where(
            or_(
                Transaction.sender_wallet_id == wallet.id,
                Transaction.receiver_wallet_id == wallet.id,
            )
        ).order_by(Transaction.created_at.desc())
    )
    transactions = result.scalars().all()

    # build pdf in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # header
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=18, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "subtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, textColor=colors.grey
    )

    elements.append(Paragraph("E-Wallet", title_style))
    elements.append(Paragraph("Transaction Statement", subtitle_style))
    elements.append(Spacer(1, 6 * mm))

    # user info
    info_style = ParagraphStyle("info", parent=styles["Normal"], fontSize=10, spaceAfter=2)
    elements.append(Paragraph(f"<b>Account Name:</b> {current_user.full_name}", info_style))
    elements.append(Paragraph(f"<b>Email:</b> {current_user.email}", info_style))
    elements.append(Paragraph(f"<b>Account Number:</b> {wallet.account_number}", info_style))
    elements.append(Paragraph(f"<b>Current Balance:</b> ₦{wallet.balance:,.2f}", info_style))
    elements.append(Paragraph(f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%d %b %Y, %I:%M %p')} UTC", info_style))
    elements.append(Paragraph(f"<b>Tier:</b> {current_user.tier.upper()}", info_style))
    elements.append(Spacer(1, 6 * mm))

    if not transactions:
        elements.append(Paragraph("No transactions found.", styles["Normal"]))
    else:
        # table headers
        table_data = [["Date", "Type", "Amount (₦)", "Status", "Narration"]]

        for tx in transactions:
            date_str = tx.created_at.strftime("%d %b %Y")
            tx_type = tx.type.value.upper()
            amount = f"{tx.amount:,.2f}"
            tx_status = tx.status.value.upper()
            narration = (tx.narration or "")[:40]  # truncate long narrations

            table_data.append([date_str, tx_type, amount, tx_status, narration])

        table = Table(
            table_data,
            colWidths=[30 * mm, 25 * mm, 35 * mm, 25 * mm, 65 * mm]
        )

        table.setStyle(TableStyle([
            # header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),

            # data rows
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()