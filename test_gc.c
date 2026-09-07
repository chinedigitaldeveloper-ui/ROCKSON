#include <stdio.h>
#include <gc.h>

int main(void) {
    GC_INIT();
    int *arr = (int *) GC_MALLOC(10 * sizeof(int));
    arr[0] = 42;
    printf("Boehm GC working! Value: %d\n", arr[0]);
    return 0;
}
