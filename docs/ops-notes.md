# Ops notes

Production rollout is controlled from the existing `hangdoivn/hangdoi-vps` deployment repository so the new measurement repository does not need a duplicate VPS SSH secret. Runtime secrets remain only in the existing production environment / VPS.
