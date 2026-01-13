#include <zsv.h>
 #include <stdio.h>
 #include <string.h>
 
 static void row_handler(void *ctx) { (void)ctx; }
 
 int main(void) {
     const char *csv = "a,b,c\n1,2,3\n";
     FILE *f = fmemopen((void*)csv, strlen(csv), "r");
     
     struct zsv_opts opts = {.stream = f, .row_handler = row_handler};
     zsv_parser parser = zsv_new(&opts);
     
     if (parser) {
         printf("Calling zsv_set_fixed_offsets(parser, 5, NULL)...\n");
         
         /* BUG: Should return error, but crashes instead */
         zsv_set_fixed_offsets(parser, 5, NULL);
         
         printf("Success! Bug is fixed.\n");
         zsv_delete(parser);
     }
     
     if (f) fclose(f);
     return 0;
 }