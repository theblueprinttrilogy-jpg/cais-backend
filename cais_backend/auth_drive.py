#!/usr/bin/env python3
"""
Autenticación para Google Drive con código de verificación
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'secrets/credentials.json'
TOKEN_FILE = 'secrets/token.json'

def main():
    creds = None
    
    # Cargar token existente
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        print("✅ Token cargado desde archivo")
    
    # Si no hay credenciales válidas
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("✅ Token refrescado")
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"❌ Error: {CREDENTIALS_FILE} no encontrado!")
                print("Por favor, asegúrate de que secrets/credentials.json existe")
                return
            
            print("🔑 Iniciando autenticación...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            
            # Usar run_console() en lugar de run_local_server()
            try:
                creds = flow.run_console()
            except Exception as e:
                print(f"Error en autenticación: {e}")
                print("Intentando con run_local_server()...")
                creds = flow.run_local_server(port=0)
        
        # Guardar token
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Token guardado en {TOKEN_FILE}")
    
    print("✅ Autenticación completada con éxito!")
    return creds

if __name__ == '__main__':
    main()
