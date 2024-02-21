/**
 * \file
 * \author Jon Doe (jon@example.com)
 * \brief Test doxygen source
 * \version 0.1
 * \date 2023-03-23
 * \copyright Copyright (c) 2023 Advanced Micro Devices Inc.
 */

/**
 * \brief Root namespace of the example project
 *
 */
namespace my_project {

/**
 * \defgroup a Group A
 * \brief The A group
 * @{
 */

/**
 * \brief A struct
 */
struct MyStruct {

    /**
     * \brief A method
     */
    void method();
};

/**
 * \brief A function inside the group
 */
void f();

/**
 * @}
 */

} // namespace my_project


/**
 * \defgroup b Group B
 */

/**
 * \ingroup b
 * \brief A function
 */
void function_outside_group();
