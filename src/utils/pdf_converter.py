#!/usr/bin/env python3
"""
PDF Converter - Múltiples métodos para convertir PDF a imágenes
OPTIMIZADO PARA PLANOS DE CONSTRUCCIÓN - 200 DPI
100% REAL - SIN PLACEHOLDERS
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from io import BytesIO
import numpy as np

# Librerías
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract


class PDFConverter:
    """
    Convierte PDFs a imágenes usando múltiples métodos.
    Optimizado para planos de construcción a 200 DPI.
    """
    
    def __init__(self, dpi: int = 200):
        """
        Inicializa el convertidor.
        
        Args:
            dpi: Resolución para la conversión (200 DPI es óptimo para planos)
        """
        self.dpi = dpi
        self.method_used = None
        self.page_count = 0
    
    def convert(self, pdf_path: str) -> List[Image.Image]:
        """
        Convierte un PDF a lista de imágenes PIL.
        Usa el primer método que funciona.
        """
        pdf_path = Path(pdf_path).expanduser()
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        
        print(f"\n📄 Convirtiendo: {pdf_path.name} (DPI: {self.dpi})")
        
        # Método 1: pdf2image (recomendado - más rápido y confiable)
        try:
            print("   [1/3] Intentando pdf2image (poppler)...")
            from pdf2image import convert_from_path
            images = convert_from_path(
                str(pdf_path), 
                dpi=self.dpi,
                size=None,
                fmt='png',
                thread_count=4
            )
            self.page_count = len(images)
            print(f"   ✅ pdf2image: {self.page_count} páginas convertidas")
            self.method_used = 'pdf2image'
            return images
        except Exception as e:
            print(f"   ⚠️ pdf2image falló: {e}")
            print("      Verifica que poppler está instalado: sudo apt install poppler-utils")
        
        # Método 2: PyMuPDF (fitz)
        try:
            print("   [2/3] Intentando PyMuPDF (fitz)...")
            import fitz
            
            images = []
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                zoom = self.dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
                img_data = pix.tobytes("png")
                img = Image.open(BytesIO(img_data))
                images.append(img)
                pix = None
            
            doc.close()
            self.page_count = len(images)
            print(f"   ✅ PyMuPDF: {self.page_count} páginas convertidas")
            self.method_used = 'pymupdf'
            return images
        except Exception as e:
            print(f"   ⚠️ PyMuPDF falló: {e}")
        
        # Método 3: pypdfium2
        try:
            print("   [3/3] Intentando pypdfium2...")
            import pypdfium2 as pdfium
            
            pdf = pdfium.PdfDocument(str(pdf_path))
            images = []
            
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                bitmap = page.render(
                    scale=self.dpi / 72,
                    rotation=0,
                    fill_color=(255, 255, 255, 255)
                )
                pil_image = bitmap.to_pil()
                images.append(pil_image)
            
            pdf.close()
            self.page_count = len(images)
            print(f"   ✅ pypdfium2: {self.page_count} páginas convertidas")
            self.method_used = 'pypdfium2'
            return images
        except Exception as e:
            print(f"   ❌ Todos los métodos fallaron: {e}")
            raise RuntimeError("No se pudo convertir el PDF a imágenes")
    
    def preprocess_image(self, img: Image.Image) -> Image.Image:
        """
        Preprocesa la imagen para mejorar el OCR.
        Optimizado para planos de construcción.
        """
        # Convertir a escala de grises
        if img.mode != 'L':
            img = img.convert('L')
        
        # Aumentar contraste (más suave que antes)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Binarización - umbral adaptativo
        img_array = np.array(img)
        threshold = np.mean(img_array) + 15
        img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
        img = Image.fromarray(img_array)
        
        # Reducción de ruido
        img = img.filter(ImageFilter.MedianFilter(size=3))
        
        return img
    
    def extract_text_with_ocr(self, images: List[Image.Image], lang: str = 'eng+spa') -> List[str]:
        """
        Extrae texto de las imágenes usando Tesseract OCR.
        """
        print(f"\n🔍 Extrayendo texto con OCR ({lang}) a {self.dpi} DPI...")
        print("-" * 40)
        
        texts = []
        config = f'--oem 3 --psm 6 -l {lang}'
        
        for idx, img in enumerate(images, 1):
            print(f"   Página {idx}...", end=' ', flush=True)
            
            img_processed = self.preprocess_image(img)
            text = pytesseract.image_to_string(img_processed, config=config)
            text = text.strip()
            texts.append(text)
            
            char_count = len(text)
            word_count = len(text.split())
            print(f"✅ {char_count} caracteres, {word_count} palabras")
        
        return texts
    
    def convert_and_extract(self, pdf_path: str, lang: str = 'eng+spa') -> Tuple[List[Image.Image], List[str]]:
        """Convierte y extrae texto en un solo paso."""
        images = self.convert(pdf_path)
        texts = self.extract_text_with_ocr(images, lang)
        return images, texts
    
    def get_image_for_page(self, pdf_path: str, page_num: int) -> Optional[Image.Image]:
        """Convierte una sola página a imagen."""
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(
                str(pdf_path),
                first_page=page_num,
                last_page=page_num,
                dpi=self.dpi
            )
            if images:
                return images[0]
        except:
            pass
        
        try:
            import fitz
            doc = fitz.open(pdf_path)
            if page_num <= len(doc):
                page = doc[page_num - 1]
                zoom = self.dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
                img_data = pix.tobytes("png")
                doc.close()
                return Image.open(BytesIO(img_data))
        except:
            pass
        
        return None


def test_converter():
    """Prueba el convertidor con un PDF real."""
    import glob
    
    print("\n" + "="*70)
    print(" PDF CONVERTER - TEST (200 DPI)")
    print("="*70)
    
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/blueprints/*.pdf')
    if not pdf_files:
        pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/INTL_*.pdf')
    
    if not pdf_files:
        print("❌ No se encontraron PDFs")
        return
    
    pdf_path = pdf_files[0]
    print(f"\n📄 PDF seleccionado: {Path(pdf_path).name}")
    print(f"   Tamaño: {Path(pdf_path).stat().st_size / 1024:.1f} KB")
    
    converter = PDFConverter(dpi=200)
    images, texts = converter.convert_and_extract(pdf_path)
    
    print(f"\n📊 RESULTADO:")
    print(f"   Páginas: {len(images)}")
    print(f"   Método usado: {converter.method_used}")
    print(f"   Texto total: {sum(len(t) for t in texts)} caracteres")
    print(f"   Palabras totales: {sum(len(t.split()) for t in texts)}")
    
    if texts and texts[0].strip():
        print(f"\n📝 Primera página (primeros 200 caracteres):")
        print("-" * 50)
        print(texts[0][:200])
        print("-" * 50)
        
        print(f"\n📊 Estadísticas por página:")
        for idx, text in enumerate(texts, 1):
            print(f"   Página {idx}: {len(text)} caracteres, {len(text.split())} palabras")
    else:
        print("⚠️ No se extrajo texto - verifica que el PDF tiene texto legible")


if __name__ == "__main__":
    test_converter()
