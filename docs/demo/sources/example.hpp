///
/// \file
/// \author Jon Doe (jon@example.com)
/// \brief Example doxygen header
/// \version 0.1
/// \date 2023-03-23
///
/// \copyright Copyright (c) 2023 Advanced Micro Devices Inc.

#include "example1.hpp"

///
/// \brief A namespace
namespace example {

///
/// \brief Example class
class Example {
public:
    ///
    /// \brief This is a method taking no arguments
    void method();

    ///
    /// \brief Example method taking parameters
    /// \param param The parameter
    /// \return description of the return value
    int method2(int param);
protected:
    ///
    /// \brief This is a protected static member
    static int static_member;
private:
    ///
    /// \brief This is a private static method
    static void static_method();
};

///
/// \brief Example class 2 to showcase class hierarchies
class Example2 : public Example {};

///
/// \brief Example of a template function
///
/// \tparam T Template parameter
/// \param a parameter
template <typename T>
void template_fun(T a);

} // namespace example

///
/// \brief A function in the global scope
///
void freestanding_function();

///
/// \defgroup group1 First Group
/// @{

///
/// \brief A struct
///
struct struct_in_group_1 {};

///
/// @}

///
/// \defgroup group2 Second Group

///
/// \brief An enumeration
/// \ingroup group2
enum Enum {
    Value1 = 1,  ///< First Enumerator
    Value2 = 17, ///< Second Enum
    Undocumented // Undocumented
};
