
import asyncio
from sqlalchemy import select
from app.database import database
from app.models import User, UserRole
from app.utils.security import get_password_hash


async def criar_admin():
    database.connect()

    async with database.session() as session:
        resultado = await session.execute(
            select(User).where(
                User.email == "admin@hospital.gov.br"
            )
        )
        usuario = resultado.scalar_one_or_none()

        if usuario:
            print("Esse e-mail já está cadastrado.")
            return

        admin = User(
            email="admin@hospital.gov.br",
            full_name="Administrador",
            hashed_password=get_password_hash("Admin12345"),
            role=UserRole.ADMIN,
            is_active=True,
        )

        session.add(admin)
        await session.commit()

        print("Administrador criado com sucesso!")

    await database.disconnect()


asyncio.run(criar_admin())