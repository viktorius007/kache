import subprocess
prefix=['python3','/private/tmp/kache-flaky/sol/run.py']
base=['./scripts/with-test-resources.sh','cargo','test','-p','kache','--bin','kache']
cases=[
('R06',['KACHE_FLAKY_PROBE=OUT_DIR'],'terminal_formatting_shares_cc_keys_with_cold_and_warm_probes'),
('R07',['KACHE_FLAKY_PROBE=NORMALIZE'],'terminal_formatting_shares_cc_keys_with_cold_and_warm_probes'),
('R08',['KACHE_FLAKY_SCHEDULER=permit'],'permit_pool_blocks_until_a_slot_is_free'),
('R09',['KACHE_FLAKY_SCHEDULER=flight'],'waiter_rechecks_after_owner_completes'),
('R10',['KACHE_FLAKY_WARMING=1'],'test_wait_for_warming_blocks_then_signals'),
('R11',['KACHE_FLAKY_HOME=1'],'test_is_macos_protected'),
('R12',['KACHE_FLAKY_WRAPPER=1'],'admit_scheduler_miss_recheck_returns_accepted_meta'),
('R13',[],'terminal_formatting_shares_cc_keys_with_cold_and_warm_probes'),
('R14',[],'scheduler::tests::'),
('R15',[],'test_wait_for_warming'),
('R16',[],'test_is_macos_protected'),
('R17',[],'admit_scheduler_miss_recheck_returns_accepted_meta'),
]
for label,env,name in cases:
 subprocess.run(prefix+[label]+(['env']+env if env else [])+base+[name,'--','--test-threads=1','--nocapture'])
