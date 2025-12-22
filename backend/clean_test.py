import asyncio
from models.database import AsyncSessionLocal
from models.models import User
from sqlalchemy import select

async def cleanup():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).filter(User.email.like('load_test_%')))
        users = result.scalars().all()
        for user in users:
            await db.delete(user)
        await db.commit()

asyncio.run(cleanup())