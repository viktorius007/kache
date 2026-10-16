import importlib.util,json,pathlib,shutil,sys,tempfile,time
spec=importlib.util.spec_from_file_location('restoration',pathlib.Path(__file__).with_name('restoration-replay.py')); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
root=module.ROOT; marker=sys.argv[1] if len(sys.argv)>1 else '__kache_root__'
case=pathlib.Path(tempfile.mkdtemp(prefix='cpp-marker-',dir=root/'fixtures'));env=module.environment(case);project=case/'project'; (project/marker).mkdir(parents=True)
(project/marker/'value.h').write_text('#define VALUE 1\n'); (project/'value.h').write_text('#define VALUE 1\n')
(project/'main.cpp').write_text('#include "'+marker+'/value.h"\n#include <cstdio>\nint main(){std::printf("%d\\n",VALUE);}\n')
(project/'Makefile').write_text('all: probe\nprobe: main.o\n\tclang++ main.o -o probe\nmain.o: main.cpp\n\t'+str(module.BASE/'kache')+' clang++ -MMD -MF main.d -c main.cpp -o main.o\n-include main.d\n')
steps=[]
def build(label):
    out=module.run(['make'],project,env,'cpp-'+marker+'-'+label)
    val=module.run([project/'probe'],project,env,'cpp-'+marker+'-'+label+'-output').strip()
    d=(project/'main.d').read_text();steps.append(dict(label=label,value=val,dep_info=d,make_output=out));print(label,val,d,flush=True);return val
build('cold')
for f in ['main.o','main.d','probe']: (project/f).unlink()
build('restore');time.sleep(1.1);(project/marker/'value.h').write_text('#define VALUE 2\n');value=build('after-header-change')
(root/'evidence'/('cpp-'+marker+'-result.json')).write_text(json.dumps(dict(case=str(case),steps=steps,expected='2',actual=value),indent=2)+'\n')
assert value=='2',f'CPP_HEADER_CHANGE_MISSED: literal {marker} header changed but executable returned {value}, expected 2'
print('CPP_HEADER_CHANGE_TRACKED',marker)
