from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from pathlib import Path
from datetime import datetime, timedelta

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent

static_dir = str(BASE_DIR / "static")
templates_dir = str(BASE_DIR / "templates")

if os.environ.get("VERCEL"):
    app.mount("/static", StaticFiles(directory="/var/task/static"), name="static")
    templates = Jinja2Templates(directory="/var/task/templates")
else:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    templates = Jinja2Templates(directory=templates_dir)

# Податкові ставки для ФОП 3-ої групи
# Для неплатників ПДВ - 5%, для платників ПДВ - 3% + 20% ПДВ
TAX_RATE_WITHOUT_VAT = 0.05
TAX_RATE_WITH_VAT = 0.03
VAT_RATE = 0.20
MILITARY_TAX_RATE = 0.01  # Військовий збір - 1%

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "result": None}
    )

def calculate_months_between_dates(start_date_str, end_date_str):
    """Розраховує кількість місяців між двома датами"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    # Додаємо 1 день до end_date, щоб включити останній день у розрахунок
    end_date = end_date + timedelta(days=1)
    
    # Розраховуємо різницю в днях
    days_diff = (end_date - start_date).days
    
    # Розраховуємо кількість місяців (приблизно)
    months = days_diff / 30.44  # Середня кількість днів у місяці
    
    # Округляємо до 2 десяткових знаків
    return round(months, 2)

@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request, 
    income: float = Form(...), 
    is_vat_payer: bool = Form(False),
    esv_amount: float = Form(1430.0),  # Мінімальний ЄСВ за замовчуванням
    esv_start_date: str = Form(...),   # Початкова дата для розрахунку ЄСВ
    esv_end_date: str = Form(...),     # Кінцева дата для розрахунку ЄСВ
    calculation_date: str = Form(None)  # Дата розрахунку
):
    # Якщо дата не вказана, використовуємо поточну
    if not calculation_date:
        calculation_date = datetime.now().strftime("%Y-%m-%d")
    
    # Розраховуємо кількість місяців між датами
    months = calculate_months_between_dates(esv_start_date, esv_end_date)

    if is_vat_payer:
        # Для платників ПДВ
        vat_amount = income * VAT_RATE / (1 + VAT_RATE)
        income_without_vat = income - vat_amount
        tax_amount = income_without_vat * TAX_RATE_WITH_VAT
        total_tax = tax_amount + vat_amount
    else:
        # Для неплатників ПДВ
        tax_amount = income * TAX_RATE_WITHOUT_VAT
        vat_amount = 0
        total_tax = tax_amount
    
    # Військовий збір (1% від доходу)
    military_tax = income * MILITARY_TAX_RATE
    
    # Додаємо ЄСВ (помножено на кількість місяців)
    total_esv = esv_amount * months
    
    # Загальна сума податків (єдиний податок + ПДВ + військовий збір + ЄСВ)
    total_tax_with_esv = total_tax + military_tax + total_esv
    
    # Чистий дохід
    net_income = income - total_tax_with_esv
    
    # Ефективна податкова ставка (у %)
    effective_tax_rate = (total_tax_with_esv / income) * 100 if income > 0 else 0

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": {
                "income": income,
                "is_vat_payer": is_vat_payer,
                "tax_amount": tax_amount,
                "vat_amount": vat_amount,
                "military_tax": military_tax,
                "military_tax_percentage": "1%",
                "esv_start_date": esv_start_date,
                "esv_end_date": esv_end_date,
                "calculation_date": calculation_date,
                "esv_amount": esv_amount,
                "months": months,
                "total_esv": total_esv,
                "total_tax": total_tax,
                "total_tax_with_esv": total_tax_with_esv,
                "net_income": net_income,
                "effective_tax_rate": effective_tax_rate
            }
        }
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000) 