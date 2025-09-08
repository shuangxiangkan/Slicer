# Driver Directory

## Overview

This directory is dedicated to generating driver programs for C/C++ library APIs.

## idea

library API fuzz driver生成的一个我觉得很好的idea：
1. 先找到library中所有有usage的API， 比如在test文件中实际使用的API
2. 根据这些API， 生成对应的fuzz driver，编译运行，获得实际可用的API的driver
3. 对那些没有usage的API，计算这些API和那些已经生成有效fuzz driver的API的相似度，找到相似度最高的那个，仿照其写法生成对应的fuzz driver
4. 采用bottom-up的方式，逐个生成所有没有usage的API的fuzz driver
   
我觉得这个idea的实现起来应该不是很难， 但是实现起来的效果应该会很好，最好情况可能会生成所有API的fuzz driver


而且还可以考虑hierarchical的关系，即一个API是基于其他API的，那么在生成这个API的fuzz driver时，就可以考虑基于那个API的fuzz driver来生成