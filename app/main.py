from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from pathlib import Path
from datetime import datetime

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

@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request, 
    income: float = Form(...), 
    is_vat_payer: bool = Form(False),
    esv_amount: float = Form(1430.0),  # Мінімальний ЄСВ за замовчуванням
    months: int = Form(1),  # Кількість місяців
    calculation_date: str = Form(None)  # Дата розрахунку
):
    # Якщо дата не вказана, використовуємо поточну
    if not calculation_date:
        calculation_date = datetime.now().strftime("%Y-%m-%d")

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