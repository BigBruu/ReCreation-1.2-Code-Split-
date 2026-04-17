from fastapi import HTTPException
from pymongo import ReturnDocument


async def assign_spaceport_to_user(db, user_id: str, username: str):
    planet = await db.planets.find_one_and_update(
        {"owner_id": None},
        {"$set": {"owner_id": user_id, "owner_username": username}},
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if not planet:
        raise HTTPException(status_code=400, detail="No available planets for spaceport")

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"spaceport_position": planet["position"]}},
    )

    return planet