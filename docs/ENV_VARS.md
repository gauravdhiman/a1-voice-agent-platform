# Environment variables

The project has three canonical root environment files. They are gitignored and
must be created locally from the committed templates:

| Template | Target | Supabase project | Selection |
|----------|--------|------------------|-----------|
| `.env.local.example` | `.env.local` | Local Supabase (`127.0.0.1:54321`) | `./start.sh start dev` |
| `.env.staging.example` | `.env.staging` | Staging (`gdzwiwukcwbqohfwxxrx`) | `./start.sh start dev --env staging` |
| `.env.prod.example` | `.env.prod` | Production (`zymiyfilulmtrmyyhvzw`) | `./start.sh start prod` / deploy |

Do not create or maintain a root `.env` file. The Compose files and scripts
select the appropriate canonical file directly.

Production environment variables are documented at:

**[05_operations/deployment/environment-variables.md](05_operations/deployment/environment-variables.md)**

Credentials templates (copy to gitignored files):

**Staging setup:** [05_operations/staging_environment.md](05_operations/staging_environment.md)

Local development configuration: [05_operations/environment_configuration.md](05_operations/environment_configuration.md)
