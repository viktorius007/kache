import importlib.util, json, os, pathlib, subprocess, tempfile
spec=importlib.util.spec_from_file_location('restoration',pathlib.Path(__file__).with_name('restoration-replay.py')); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
root=module.ROOT
case=pathlib.Path(tempfile.mkdtemp(prefix='permissions-',dir=root/'fixtures')); env=module.environment(case)
mount=case/'volume'; mount.mkdir(); image=case/'fixture.dmg'
commands=[]
def run(argv):
    commands.append([str(a) for a in argv]); p=subprocess.run([str(a) for a in argv],cwd=case,env=env,capture_output=True,text=True,timeout=90)
    print('ARGV',json.dumps(commands[-1]),'EXIT',p.returncode,p.stdout,p.stderr,flush=True)
    assert p.returncode==0, 'fixture command failed'
    return p.stdout
attached=False
try:
    run(['hdiutil','create','-size','24m','-fs','HFS+','-volname','kache-fixture',image])
    run(['hdiutil','attach','-nobrowse','-mountpoint',mount,image]); attached=True
    # Paths remain under the generated fixture even though filesystem differs.
    env['KACHE_CACHE_DIR']=str(mount/'cache'); pathlib.Path(env['KACHE_CACHE_DIR']).mkdir()
    assert pathlib.Path(env['KACHE_CACHE_DIR']).resolve().is_relative_to(root.resolve())
    deps=module.BASE/'deps'; out=case/'permission-probe'
    args=['rustc','--edition=2024',root/'permission-probe.rs','-L','dependency='+str(deps),'--extern','kache_store='+str(next(deps.glob('libkache_store-*.rlib'))),'-o',out]
    env['RUSTC_WRAPPER']=''
    module.run(args,case,env,'permissions-compile')
    module.run([out,case,'independent'],case,env,'permissions-apfs-control')
    (mount/'independent-case').mkdir()
    module.run([out,mount/'independent-case','independent'],case,env,'permissions-hfs-independent-control')
    module.run([out,mount,'shared'],case,env,'permissions-public-api')

finally:
    if attached:
        run(['hdiutil','detach',mount])
    (root/'evidence/permission-commands.json').write_text(json.dumps(dict(case=str(case),commands=commands),indent=2)+'\n')
