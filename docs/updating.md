# Updating

You can update a music player installation as follows:

1. Enter the correct directory
2. Run `docker compose pull` to download new images
3. Check the [migrations](./migrations.md) wiki page to see if there were any new database migrations since your previous update.
4. Run `docker compose up -d` to recreate the containers
