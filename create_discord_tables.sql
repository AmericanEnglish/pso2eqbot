CREATE TABLE discord_guild_table (
    guild_id TEXT,
    default_channel_id TEXT,
    timezone TEXT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE discord_user_table (
    user_id TEXT,
    timezone TEXT,
    PRIMARY KEY (user_id)
)
