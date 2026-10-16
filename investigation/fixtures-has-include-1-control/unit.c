#if __has_include("optional.h")
#include "optional.h"
#else
#define VALUE 1
#endif
int main(void) { return VALUE; }
