# -*- coding: utf-8 -*-
"""
invoice_parser.py
------------------
Azərbaycan Elektron qaimə-faktura (VÖEN portalının PDF export-u) faylından
başlıq məlumatlarını və mal cədvəlini çıxaran modul.

Bu modul PDF-in HƏMİŞƏ eyni arxitekturaya (sütun sırası və başlıq strukturu)
malik olduğunu qəbul edir. Sətir sayı dəyişə bilər, sütun sayı (18) sabitdir.
"""

import re
import pdfplumber

NUM_RE = re.compile(r'^-?\d+(\.\d+)?$')
CODE_RE = re.compile(r'^\d{10}$')  # Malın kodu (HS kodu) həmişə 10 rəqəmdir

# Cədvəlin 18 sütununun adları (qaimədəki 1..18 nömrələnməsi ilə eyni sıra)
COLUMNS = [
    "Sıra №-si",
    "Malın (işin, xidmətin) adı",
    "Malın (işin, xidmətin) kodu",
    "GTİN",
    "Ölçü vahidi",
    "Miqdarı, həcmi",
    "Vahidinin satış qiyməti (manatla)",
    "Cəmi məbləği (manatla)",
    "Aksiz dərəcəsi",
    "Aksiz məbləği (manatla)",
    "Malın dəyəri (ƏDV-siz, manatla)",
    "ƏDV 18% dəyəri (manatla)",
    "ƏDV 0% dəyəri (manatla)",
    "ƏDV-dən azad dəyəri (manatla)",
    "ƏDV-yə cəlb edilməyən dəyəri (manatla)",
    "ƏDV məbləği (manatla)",
    "Yol vergisi (manatla)",
    "Yekun məbləğ (manatla)",
]

HEADER_FIELDS_ORDER = [
    "Seriya", "Nömrə", "Tarix", "Növü",
    "Göndərən VÖEN", "Göndərən",
    "Qəbul edən VÖEN", "Qəbul edən",
    "Əsas",
    "Yekun məbləğ (rəqəmlə)", "Yekun məbləğ (yazı ilə)",
]


class InvoiceParseError(Exception):
    pass


def _try_parse_row(tokens):
    """Bir sətirdəki tokenləri cədvəl sətrinə çevirməyə çalışır.
    Uğurlu olarsa dict, olmazsa None qaytarır."""
    code_idx = None
    for idx, tok in enumerate(tokens):
        if CODE_RE.fullmatch(tok):
            code_idx = idx
            break
    if code_idx is None:
        return None

    after = tokens[code_idx + 1:]
    if len(after) < 14:  # ən azı: ölçü vahidi + 13 rəqəm
        return None

    nums_candidates = after[-13:]
    if not all(NUM_RE.fullmatch(t) for t in nums_candidates):
        return None

    remainder = after[:-13]
    if len(remainder) == 0:
        return None

    unit = remainder[-1]
    gtin = remainder[-2] if len(remainder) >= 2 else ''

    pre = tokens[:code_idx]
    sira = None
    name_tokens = pre
    if pre and re.fullmatch(r'\d{1,3}', pre[0]):
        sira = pre[0]
        name_tokens = pre[1:]

    name = ' '.join(name_tokens)
    nums = [float(x) for x in nums_candidates]

    return {
        'sira': sira,
        'name': name,
        'code': tokens[code_idx],
        'gtin': gtin,
        'unit': unit,
        'nums': nums,
    }


def _extract_table_rows(lines):
    start_idx = None
    end_idx = None
    for i, l in enumerate(lines):
        ls = l.strip()
        if start_idx is None and re.match(r'^1\s+2\s+3\s+4\s+5\s+6\s+7\s+8', ls):
            # sütun nömrələnməsi sətri (1 2 3 4 ... 18) - cədvəl bundan sonra başlayır
            start_idx = i + 1
            continue
        if start_idx is not None and ls.startswith('Cəmi '):
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        raise InvoiceParseError(
            "Cədvəlin başlanğıc/son sərhədləri tapılmadı. "
            "PDF formatı gözlənilən qaimə arxitekturasına uyğun olmaya bilər."
        )

    region = lines[start_idx:end_idx]
    rows = []
    buffer = []
    i = 0
    while i < len(region):
        line = region[i].strip()
        if not line:
            i += 1
            continue
        tokens = line.split()
        parsed = _try_parse_row(tokens)
        if parsed:
            prefix = ' '.join(buffer).strip()
            buffer = []
            name = (prefix + ' ' + parsed['name']).strip()
            # Ad tamamilə qonşu sətirlərə düşübsə (bu sətirdə ad yoxdursa),
            # növbəti sətrin ad artığı olub-olmadığını yoxla.
            if parsed['name'] == '' and i + 1 < len(region):
                nxt = region[i + 1].strip()
                nxt_tokens = nxt.split()
                if nxt and not any(CODE_RE.fullmatch(t) for t in nxt_tokens) \
                        and not nxt.startswith('Cəmi') and len(nxt_tokens) <= 8:
                    name = (name + ' ' + nxt).strip()
                    i += 1
            row = [
                parsed['sira'], name, parsed['code'], parsed['gtin'], parsed['unit']
            ] + parsed['nums']
            rows.append(row)
        else:
            buffer.append(line)
        i += 1

    if not rows:
        raise InvoiceParseError("Cədvəldə heç bir mal sətri tapılmadı.")

    return rows


def _extract_header(full_text):
    header = {}

    m = re.search(r'Seriya:\s*(\S+)\s+Nömrə:\s*(\S+)\s+Tarix:\s*([\d.]+\s+[\d:]+)', full_text)
    if m:
        header['Seriya'] = m.group(1)
        header['Nömrə'] = m.group(2)
        header['Tarix'] = m.group(3)

    m = re.search(r'Növü:\s*(\S+)', full_text)
    if m:
        header['Növü'] = m.group(1)

    m = re.search(r'Göndərən:\s*VÖEN((?:\s\d){10})\s+(.+)', full_text)
    if m:
        header['Göndərən VÖEN'] = m.group(1).replace(' ', '')
        header['Göndərən'] = m.group(2).strip()

    m = re.search(r'Qəbul edən:\s*VÖEN((?:\s\d){10})\s+(.+)', full_text)
    if m:
        header['Qəbul edən VÖEN'] = m.group(1).replace(' ', '')
        header['Qəbul edən'] = m.group(2).strip()

    m = re.search(r'Əsas\s+(.+?)\n', full_text)
    if m:
        header['Əsas'] = m.group(1).strip()

    m = re.search(r'Yekun məbləğ\s+(\d+\s*\(.+?)\n', full_text)
    if m:
        header['Yekun məbləğ (yazı ilə)'] = m.group(1).strip()

    m2 = re.search(r'Yekun məbləğ\s+(\d+)\s*\(.+?manat\s+(\d+)\s*\(', full_text)
    if m2:
        header['Yekun məbləğ (rəqəmlə)'] = f"{m2.group(1)}.{m2.group(2)}"

    return header


def parse_invoice(pdf_path):
    """PDF-i açır, başlıq və cədvəl məlumatlarını çıxarır.

    Returns:
        (header: dict, rows: list[list], columns: list[str])
    """
    with pdfplumber.open(pdf_path) as pdf:
        texts = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
        full_text = "\n".join(texts)

    if not full_text.strip():
        raise InvoiceParseError(
            "PDF-dən mətn oxunmadı. Fayl skan edilmiş şəkil ola bilər "
            "(mətn qatı yoxdur)."
        )

    lines = full_text.split('\n')
    rows = _extract_table_rows(lines)
    header = _extract_header(full_text)
    return header, rows, COLUMNS
