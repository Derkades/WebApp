# Updating

You can update a music player installation as follows:

1. Enter the correct directory
2. Run `docker compose pull` to download new images
3. If your previous update was before 2023-10-28, use the [migrations wiki page](./migrations.md) to update your database.
4. Run `docker compose up -d` to recreate the containers
