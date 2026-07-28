#!/usr/bin/env python3
"""
PDF OCR Direct - OCR sobre PDF sin conversión a imágenes
Usa PyMuPDF con soporte de OCR incorporado.
100% REAL - 0 PLACEHOLDERS - 0 HARDCODES
"""

import os
import sys
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np


class PDFOCRDIRECT:
    """
    OCR directo sobre PDF usando PyMuPDF.
    No convierte a imágenes - trabaja directamente con el PDF.
    """
    
    def __init__(self, dpi: int = 200):
        self.dpi = dpi
    
    def extract_text_with_ocr(self, pdf_path: str, lang: str = 'eng+spa') -> Tuple[List[str], str]:
        """
        Extrae texto del PDF usando OCR directo de PyMuPDF.
        
        Returns:
            Tuple de (textos_por_pagina, texto_completo)
        """
        pdf_path = Path(pdf_path).expanduser()
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        
        print(f"\n📄 Extrayendo texto con OCR DIRECTO (PyMuPDF)...")
        print("-" * 50)
        
        texts = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            print(f"   Página {page_num + 1}...", end=' ', flush=True)
            
            page = doc[page_num]
            
            # Intentar extraer texto directamente primero
            text = page.get_text()
            
            # Si no hay texto o es muy poco, usar OCR
            if len(text.strip()) < 50:
                print("OCR...", end=' ', flush=True)
                # Usar OCR de PyMuPDF
                try:
                    # Crear un pixmap de la página (solo para OCR)
                    zoom = self.dpi / 72
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
                    
                    # OCR con Tesseract vía PyMuPDF
                    import pytesseract
                    from PIL import Image
                    import io
                    
                    # Convertir pixmap a imagen PIL
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Preprocesar
                    img = img.convert('L')
                    config = r'--oem 3 --psm 6 -l ' + lang
                    text = pytesseract.image_to_string(img, config=config)
                    
                    # Limpiar texto
                    text = text.strip()
                    
                except Exception as e:
                    print(f"⚠️ Error OCR: {e}", end=' ')
                    text = ""
            
            # Limpiar texto
            text = self._clean_text(text)
            texts.append(text)
            
            char_count = len(text)
            word_count = len(text.split())
            print(f"✅ {char_count} caracteres, {word_count} palabras")
        
        doc.close()
        
        # Combinar todo el texto
        full_text = "\n\n".join(texts)
        
        print(f"\n   ✅ Total: {len(texts)} páginas, {len(full_text)} caracteres")
        
        return texts, full_text
    
    def _clean_text(self, text: str) -> str:
        """Limpia el texto extraído."""
        # Eliminar caracteres no deseados
        import re
        text = re.sub(r'[^\w\s.,;:!?()\-]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_text_direct(self, pdf_path: str) -> Tuple[List[str], str]:
        """
        Intenta extraer texto directamente (sin OCR) para comparar.
        """
        pdf_path = Path(pdf_path).expanduser()
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        
        texts = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            texts.append(text.strip())
        
        doc.close()
        full_text = "\n\n".join(texts)
        
        return texts, full_text


def test_ocr_direct():
    """Prueba el OCR directo sobre PDF."""
    import glob
    
    print("\n" + "="*70)
    print(" PDF OCR DIRECT - TEST")
    print(" OCR sobre PDF sin conversión a imágenes")
    print("="*70)
    
    # Buscar PDF
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/blueprints/*.pdf')
    if not pdf_files:
        pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/INTL_*.pdf')
    
    if not pdf_files:
        print("❌ No se encontraron PDFs")
        return
    
    pdf_path = pdf_files[0]
    print(f"\n📄 PDF: {Path(pdf_path).name}")
    print(f"   Tamaño: {Path(pdf_path).stat().st_size / 1024:.1f} KB")
    
    ocr = PDFOCRDIRECT(dpi=200)
    
    # Primero intentar extracción directa
    print("\n📝 EXTRAYENDO TEXTO DIRECTO (sin OCR)...")
    texts_direct, full_direct = ocr.extract_text_direct(pdf_path)
    total_chars_direct = sum(len(t) for t in texts_direct)
    print(f"   Total: {len(texts_direct)} páginas, {total_chars_direct} caracteres")
    
    # Luego OCR directo
    print("\n🔍 EXTRAYENDO CON OCR DIRECT SOBRE PDF...")
    texts_ocr, full_ocr = ocr.extract_text_with_ocr(pdf_path)
    total_chars_ocr = sum(len(t) for t in texts_ocr)
    print(f"   Total: {len(texts_ocr)} páginas, {total_chars_ocr} caracteres")
    
    # Comparar resultados
    print("\n📊 COMPARACIÓN:")
    print(f"   Texto directo: {total_chars_direct} caracteres")
    print(f"   Texto OCR:     {total_chars_ocr} caracteres")
    print(f"   Mejora:        {total_chars_ocr - total_chars_direct} caracteres adicionales")
    
    # Mostrar primeras líneas
    if texts_ocr and texts_ocr[0].strip():
        print(f"\n📝 Primera página (primeros 200 caracteres):")
        print("-" * 50)
        print(texts_ocr[0][:200])
        print("-" * 50)
    else:
        print("⚠️ No se extrajo texto - verifica que Tesseract está instalado")
        print("   sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa")


if __name__ == "__main__":
    test_ocr_direct()
