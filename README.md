```sh
export deployed_region=us-central1

# Deploy to GC
!adk deploy agent_engine --project=$GOOGLE_CLOUD_PROJECT --region=$deployed_region charla_facil --agent_engine_config_file=charla_facil/.agent_engine_config.json
```
