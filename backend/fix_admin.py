import asyncio

import asyncpg


async def fix():
    conn = await asyncpg.connect(
        'postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict'
    )
    hash_val = '$2b$12$1MW2RsqhgVR6PkfLjsFxkugsTxPkbNHrDM7PmICMdPulpXsD2d99y'
    await conn.execute(
        'UPDATE users SET hashed_password = $1 WHERE email = $2', hash_val, 'admin@hospital.gov.br'
    )
    await conn.close()
    print('Senha admin atualizada para admin123')


asyncio.run(fix())
