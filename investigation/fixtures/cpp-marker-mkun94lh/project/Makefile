all: probe
probe: main.o
	clang++ main.o -o probe
main.o: main.cpp
	/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache clang++ -MMD -MF main.d -c main.cpp -o main.o
-include main.d
