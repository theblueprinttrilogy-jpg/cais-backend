import asyncio
from app.services.drive_sync_service import DriveSyncService
from app.services.zip_code_service import ZipCodeService

async def main():
    # Inicializar servicio de Drive y pasarlo al servicio de Zip
    drive_service = DriveSyncService()
    service = ZipCodeService(drive_service=drive_service)

    # 1. Probar Los Angeles (90001)
    la_status = await service.lookup_jurisdiction("90001")
    print("LA (90001) Regulatory Status:", la_status)
    la_covered = await service.is_fully_covered("90001")
    print("Is LA fully covered?", la_covered)

    print("-" * 50)

    # 2. Probar Beverly Hills (90210)
    bh_status = await service.lookup_jurisdiction("90210")
    print("Beverly Hills (90210) Regulatory Status:", bh_status)
    bh_covered = await service.is_fully_covered("90210")
    print("Is Beverly Hills fully covered?", bh_covered)

if __name__ == "__main__":
    asyncio.run(main())
