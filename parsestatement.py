import json
import sys
import timestring
import re
import jinja2
import csv
import collections
from os import path

TEMPLATE_FILENAME = 'template.html'
STATEMENT_HTML_FILE = 'expense.html'
ERROR = []


def CsvToJson(csvfile):
    transactions = []
    fieldnames = ("Date", "Narration", "Value Dat", "Debit Amount",
                  "Credit Amount", "Chq/Ref Number", "Closing Balance")
    reader = csv.DictReader(csvfile, fieldnames)
    for idx, row in enumerate(reader):
        for d in row:
            if type(row[d]) is not list:
                row[d] = row[d].lstrip().rstrip()
        if idx > 0:
            transactions.append(row)
    return transactions


def SetTransactionDetail(newtran, tran, merchant, mode):
    if tran['Debit Amount'] > 0:
        newtran['Type'] = "Debit"
        newtran['Amount'] = tran['Debit Amount']
    else:
        newtran['Type'] = "Credit"
        newtran['Amount'] = tran['Credit Amount']
    newtran['Merchant'] = merchant
    newtran['Mode'] = mode

def ParseTransactions(transactions):
    statement = []

    for tran in transactions:
        newtran = {}
        td = tran['Date'].split('/')
        tran['Date'] = td[1]+'/'+td[0]+'/'+td[2]
        month = timestring.Date(tran['Date']).date.strftime('%B')
        year = timestring.Date(tran['Date']).date.strftime('%Y')
        nbregex = re.compile('^[a-zA-Z0-9]+/.*$')
        swiftregex = re.compile('^[a-zA-Z0-9]+$')
        newtran['Month'] = month
        newtran['Year'] = year

        if "/" in tran["Debit Amount"]:
            tran["Debit Amount"] = 0.00
        elif "/" in tran["Credit Amount"]:
            tran["Credit Amount"] = 0.00
        else:
            tran["Debit Amount"] = round(float(tran['Debit Amount']), 2)
            tran["Credit Amount"] = round(float(tran['Credit Amount']), 2)

        # ATM Withdrawls Transactions
        if (tran['Narration'].startswith("ATW")):
            SetTransactionDetail(newtran, tran, MerchantName, "Card")

        # Credit Card Bill Pay Transactions
        elif (tran['Narration'].startswith("CC ") or tran['Narration'].startswith("IB BILLPAY")):
            MerchantName = "CreditCard BillPay"
            SetTransactionDetail(newtran, tran, MerchantName, "Card")

        # Card DEBIT/CREDIT Transactions
        elif (tran['Narration'].startswith("POS") or tran['Narration'].startswith("ME DC SI") or tran['Narration'].startswith("CRV")):
            if tran['Narration'].startswith("POS REF"):
                try:
                    MerchantName = tran['Narration'].split(' ')[3]
                except:
                    MerchantName = tran['Narration']
                    ERROR.append("Error Split - " + MerchantName)
            elif tran['Narration'].startswith("ME DC SI"):
                try:
                    MerchantName = tran['Narration'].split(' ')[4]
                except:
                    MerchantName = tran['Narration']
                    ERROR.append("Error Split - " + MerchantName)
            elif tran['Narration'].startswith("CRV"):
                try:
                    MerchantName = tran['Narration'].split(' ')[3]
                except:
                    MerchantName = tran['Narration']
                    ERROR.append("Error Split - " + MerchantName)
            elif tran['Narration'].startswith("POS"):
                try:
                    MerchantName = tran['Narration'].split(' ')[2]
                except:
                    MerchantName = tran['Narration']
                    ERROR.append("Error Split - " + MerchantName)
            SetTransactionDetail(newtran, tran, MerchantName, "Card")

        # UPI DEBIT Transactions
        elif (tran['Narration']).startswith("UPI"):
            try:
                MerchantName = tran['Narration'].split('-')[1]
            except:
                MerchantName = tran['Narration']
                ERROR.append("Error Split - " + MerchantName)
            SetTransactionDetail(newtran, tran, MerchantName, "UPI")

        # IMPS DEBIT/CREDIT Transactions
        elif tran['Narration'].startswith("IMPS"):
            try:
                MerchantName = tran['Narration'].split('-')[2]
            except:
                MerchantName = tran['Narration']
                ERROR.append("Error Split - " + MerchantName)
            SetTransactionDetail(newtran, tran, MerchantName, "IMPS")

        # Reverese IMPS DEBIT/CREDIT Transactions
        elif tran['Narration'].startswith("REV-IMPS"):
            try:
                MerchantName = tran['Narration'].split('-')[3]
            except:
                MerchantName = tran['Narration']
                ERROR.append("Error Split - " + MerchantName)
            SetTransactionDetail(newtran, tran, MerchantName, "IMPS")

        # NEFT DEBIT/CREDIT Transactions
        elif tran['Narration'].startswith("NEFT"):
            try:
                MerchantName = tran['Narration'].split('-')[2]
            except:
                MerchantName = tran['Narration']
                ERROR.append("Error Split - " + MerchantName)
            SetTransactionDetail(newtran, tran, MerchantName, "NEFT")

        # Cheque DEBIT Transactions
        elif tran['Narration'].startswith("CHQ") and tran['Debit Amount'] > 0:
            if 'INWARD' in tran['Narration']:
                try:
                    MerchantName = tran['Narration'].split(
                        'PAID-INWARD')[1].rstrip().lstrip()
                except:
                    MerchantName = tran['Narration']
                    ERROR.append("Error Split - " + MerchantName)
            else:
                try:
                    MerchantName = tran['Narration'].split(
                        'CTS-MU-')[1].rstrip().lstrip()
                except:
                    MerchantName = tran['Narration']
                    ERROR.append("Error Split - " + MerchantName)
            SetTransactionDetail(newtran, tran, MerchantName, "Cheque")

        # Net Banking DEBIT Transactions
        elif nbregex.match(tran['Narration']) and tran['Debit Amount'] > 0:
            try:
                MerchantName = tran['Narration'].split('/')[1]
            except:
                MerchantName = tran['Narration']
                ERROR.append("Error Split - " + MerchantName)
            SetTransactionDetail(newtran, tran, MerchantName, "Net Banking")

        # SWIFT CREDIT Transactions
        elif swiftregex.match(tran['Narration']):
            MerchantName = "International Credit"
            newtran['Merchant'] = MerchantName
            SetTransactionDetail(newtran, tran, MerchantName, "Swift Transaction")

        # Bank fee DEBIT/CREDIT related Transactions
        elif (tran['Narration'].startswith(".") or tran['Narration'].startswith("DEBIT CARD PUR") or tran['Narration'].startswith("CREDIT INTEREST CAPITALISED")):
            MerchantName = "Bank"
            SetTransactionDetail(newtran, tran, MerchantName, "Bank Transaction")

        # This are inter account transactions example saving to current
        elif tran['Narration'].startswith("FT -"):
            MerchantName = "Bank"
            SetTransactionDetail(newtran, tran, MerchantName, "Inter Account Transaction")

        # CBDT Income Tax DEBIT Transactions
        elif "CBDT TAX" in tran['Narration'] and tran['Debit Amount'] > 0:
            MerchantName = "CBDT TAX"
            SetTransactionDetail(newtran, tran, MerchantName, "Net Banking")

        else:
            try:
                if tran['Credit Amount'] > 0 or tran['Debit Amount'] > 0:
                    ERROR.append("Unidentified Transaction - " + tran['Narration'])
            except:
                pass

        if len(newtran) > 3:
            statement.append(newtran)

    return statement


def GenerateHtml(statement, AVG_MONTHLY_SPEND, AVG_MONTHLY_EARN, TOTAL_BALANCE, TOTAL_CREDIT, TOTAL_DEBIT):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(["./"]), autoescape=True)
    template = env.get_template(TEMPLATE_FILENAME)
    rendered = template.render(results=json.dumps(statement), AVG_MONTHLY_EARN=AVG_MONTHLY_EARN,
                               AVG_MONTHLY_SPEND=AVG_MONTHLY_SPEND, TOTAL_DEBIT=TOTAL_DEBIT, TOTAL_CREDIT=TOTAL_CREDIT, TOTAL_BALANCE=TOTAL_BALANCE)
    with open(STATEMENT_HTML_FILE, 'wb') as f:
        f.write(rendered.encode("utf-8"))


def DictMaker():
    return collections.defaultdict(DictMaker)


def CalculateAverage(transactions):
    MONTHS_DEBIT = []
    MONTHS_CREDIT = []
    TOTAL_DEBIT = 0.00
    TOTAL_CREDIT = 0.00
    for tran in transactions:
        tran['Amount'] = float(tran['Amount'])
        if tran['Type'] == 'Debit' and tran['Amount'] > 0:
            TOTAL_DEBIT += tran['Amount']
            if tran['Month']+tran['Year'] not in MONTHS_DEBIT:
                MONTHS_DEBIT.append(tran['Month']+tran['Year'])
        elif tran['Type'] == 'Credit' and tran['Amount'] > 0:
            TOTAL_CREDIT += tran['Amount']
            if tran['Month']+tran['Year'] not in MONTHS_CREDIT:
                MONTHS_CREDIT.append(tran['Month']+tran['Year'])

    return round(TOTAL_DEBIT/len(MONTHS_DEBIT), 2), round(TOTAL_CREDIT/len(MONTHS_CREDIT), 2), round(TOTAL_CREDIT - TOTAL_DEBIT, 2), round(TOTAL_CREDIT, 2), round(TOTAL_DEBIT, 2)


def main():
    STATEMENT_CSV_FILE = sys.argv[1]
    if path.exists(STATEMENT_CSV_FILE):
        csvfile = open(STATEMENT_CSV_FILE, 'r')
    else:
        ERROR.append("Error - Statement file not found")
        return ERROR
    transactions = CsvToJson(csvfile)
    statement = ParseTransactions(transactions)
    AVG_MONTHLY_SPEND, AVG_MONTHLY_EARN, TOTAL_BALANCE, TOTAL_CREDIT, TOTAL_DEBIT = CalculateAverage(statement)
    GenerateHtml(statement, AVG_MONTHLY_SPEND, AVG_MONTHLY_EARN, TOTAL_BALANCE, TOTAL_CREDIT, TOTAL_DEBIT)
    return ERROR

if len(sys.argv) > 1:
    ERROR = main()
    for err in ERROR:
        print(err) #prints error if there was any
else:
    print("Statement not passed")
    print("Usage - " + sys.argv[0] + " <dellimetied_statement.txt> ")
