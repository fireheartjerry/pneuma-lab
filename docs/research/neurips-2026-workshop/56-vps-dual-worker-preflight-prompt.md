# 56 - VPS dual-worker preflight prompt

**Status:** local Linux handoff only; no cloud operation or scientific
execution is authorized by this document.

Paste the following into the VPS session after this branch has been pushed.

```text
You are performing only the Linux/VPS preflight for Pneuma Lab's dual-L40S
Spot topology. This is not an authorization to launch, plan, provision, or
run any empirical work.

Hard boundaries
- Do not run `terraform apply`, `terraform destroy`, `aws ...`, `aws batch`,
  an ECR push, or any command that creates, changes, or tears down cloud
  resources.
- Do not start a GPU instance, container, model, benchmark, pilot, Step 4A,
  Step 4B, or official experiment. Do not spend AWS credit.
- Do not produce, unblind, promote, or interpret a scientific result.
- Do not commit, push, edit the append-only execution journal, or edit the
  canonical project-status manifest. Stop and report if the checkout is not
  clean after the permitted private-config migration below.
- Treat every remote state or credential as out of scope. Do not inspect or
  print secrets, account IDs, image references, tokens, or private tfvars
  values.

Required work
1. Start from a fresh checkout of branch `codex/neurips-2026-empirical` and
   verify the received commit is the current remote branch head. Run
   `git status --short`; it must be clean before any permitted local change.
2. Read `AGENTS.md`, `docs/project-status.json`,
   `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md`,
   `docs/research/neurips-2026-workshop/55-dual-l40s-spot-topology-reconciliation.md`,
   and this document. Preserve their gates exactly.
3. If the ignored file `infra/terraform/environments/aws-private.tfvars`
   exists, make the one mechanical local migration it requires: rename the
   key `controller_image` to `gpu_worker_image`, preserving its value without
   displaying it. Do not add this ignored file to Git. If it does not exist,
   report that fact and do not create one.
4. Run only these local, bounded checks. Do not substitute an account-bound
   Terraform plan or an AWS command:

   python -m pneuma_lab.status --check
   python -m pytest tests/cloud/test_architecture.py tests/cloud/test_aws_account.py tests/cloud/test_pilot.py tests/cloud/test_pilot_admission_receipt.py tests/cloud/test_worker_allocation.py tests/cloud/test_iac_plan.py tests/test_schema_loads.py -q
   terraform -chdir=infra/terraform fmt -check main.tf iam.tf variables.tf
   terraform -chdir=infra/terraform/bootstrap-verification fmt -check main.tf variables.tf
   git diff --check

   Each test command has a 60-second ceiling. If a required executable is
   absent, report the missing dependency; do not install, upgrade, or alter
   locked dependencies without a separate instruction.
5. Return a concise report containing: commit SHA, each command's pass/fail
   status, whether the private variable rename was completed (never its
   value), and an explicit statement that no AWS action, cloud spend, model
   run, pilot, or experiment occurred.

Stop there. A later, explicit authorization is required before a fresh
account/capacity/pricing receipt, Terraform L1/L3 work, per-worker GPU
admission, recovery drill, or any real experiment.
```
