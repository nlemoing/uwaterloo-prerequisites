from bs4 import BeautifulSoup
from urllib.request import urlopen

#error code 0: invalid subject
#error code 1: course not found
def get_prereq_string(subject, number):
    url = "http://www.ucalendar.uwaterloo.ca/1718/COURSE/course-{}.html"
    course_name = subject + " " + number
    try:
        courses_page = urlopen(url.format(subject))
    except:
        return 0
    soup = BeautifulSoup(courses_page, 'html.parser')
    def correct_link(tag):
        return tag.name == "a" and tag.has_attr('name') and tag['name'] == subject + number
    course = soup.find(correct_link)
    if not course:
        return 1
    course = course.find_parent("table")
    for string in course.strings:
        if "Prereq" in string:
            return string[8:].rstrip('.')
    return ""

bracket_objects_list = []
bracket_string = "xxx"

def parse_prereq_string(string):
    if ";" in string:
        return make_prereq_obj(string, "; ")
    elif "(" in string: #take care of parenthesis
        return bracket_parse(string)
    elif string == bracket_string:
        return bracket_objects_list.pop(0)
    elif "students" in string:
        return PrereqMisc(string)
    elif " with " in string or " in " in string: #parse the grades
        return grade_parse(string)
    elif "ne of" in string:
        string = string.upper()
        string = string.replace("ONE OF ", "")
        string = string.replace(", OR", " or")
        string = string.replace(",", " or")
        string = string.replace("OR", "or")
        return parse_prereq_string(string)
    elif " and " in string or ", " in string or "&" in string:
        string = string.replace(", ", " and ")
        string = string.replace("&", "and")
        return make_prereq_obj(string, " and ")
    elif " or " in string or "/" in string:
        string = string.replace("/", " or ")
        return make_prereq_obj(string, " or ")
    elif string[:3].isnumeric():
        return Course(Course.last_subject, string)
    elif is_course_code(string):
        the_course = string.split()
        Course.last_subject = the_course[0]
        return Course(the_course[0], the_course[1])
    else:
        return PrereqMisc(string)

def is_course_code(string):
    the_course = string.split()
    return len(the_course) == 2 and the_course[1][:3].isnumeric()

#general parser
def make_prereq_obj(string, split):
    if split == " or ":
        prereq = PrereqOr()
    else:
        prereq = PrereqAnd()
    splinters = string.split(split)
    for splinter in splinters:
        prereq.add(parse_prereq_string(splinter))
    return prereq

def grade_parse(string):
    if " in " in string:
        splinter = string.split(" in ", 1)
        prereq = parse_prereq_string(splinter[1])
        grade_str = splinter[0]
    else:
        splinter = string.split(" with ", 1)
        prereq = parse_prereq_string(splinter[0])
        grade_str = splinter[1]
    percent_index = grade_str.find("%")
    grade = int(grade_str[percent_index - 2:percent_index])
    prereq.setmingrade(grade)
    grade_str = grade_str.replace("or higher", "")
    if "or" in grade_str:
        splinter = grade_str.split(" or ", 1)
        if not "grade" in splinter[0]:
            other_course = parse_prereq_string(splinter[0])
        else:
            other_course = parse_prereq_string(splinter[1])
        combined = PrereqOr()
        combined.add(prereq)
        combined.add(other_course)
        return combined
    return prereq

def bracket_parse(string):
    open_bracket = string.find("(")
    close_bracket = find_closing_bracket(string[open_bracket + 1:]) + open_bracket + 1
    prereq_string = string[open_bracket:close_bracket]
    bracket_objects_list.append(parse_prereq_string(prereq_string[1:-1]))
    return parse_prereq_string(string.replace(prereq_string, bracket_string))

def find_closing_bracket(string):
    depth = 1
    index = 0
    while (depth != 0):
        if string[index] == "(":
            depth = depth + 1
        elif string[index] == ")":
            depth = depth - 1
        index = index + 1
    return index

##classes


class Course:
    last_subject = ""
    def __init__(self, subject, number, grade = 0):
        self.subject = subject
        self.number = number
        self.mingrade = 0
        self.grade = grade
    def __str__(self):
        ret_str = self.subject + " " + self.number
        if (self.mingrade):
            ret_str = ret_str + " (" + str(self.mingrade) + "%)"
        return ret_str
    def eval(self, classlst):
        for course in classlst:
            if course.subject == self.subject and course.number == self.number and course.grade >= self.mingrade:
                return True
        return False
    def setmingrade(self, grade):
        self.mingrade = grade
    def tolist(self):
        ret = []
        ret.append(self)
        return ret

class Prereq:
    def __init__(self):
        self.items = []
    def add(self, item):
        self.items.append(item)
    def setmingrade(self, grade):
        for item in self.items:
            item.setmingrade(grade)

class PrereqMisc:
    def __init__(self, info):
        self.info = info
    def __str__(self):
        return self.info
    def eval(self, classlst):
        if self.info == "instructor consent":
            return False
        else:
            return True
    def tolist(self):
        return [self.info]
    def setmingrade(self, grade):
        pass

class PrereqOr(Prereq):
    def __str__(self):
        theString = "(or"
        for item in self.items:
            theString = theString + " " + item.printPR()
        theString = theString + ")"
        return theString
    def eval(self, classlst):
        for item in self.items:
            if item.eval(classlst):
                return True
        return False
    def tolist(self):
        return self.items[0].tolist()

class PrereqAnd(Prereq):
    def __str__(self):
        theString = "(and"
        for item in self.items:
            theString = theString + " " + item.printPR()
        theString = theString + ")"
        return theString
    def eval(self, classlst):
        for item in self.items:
            if not item.eval(classlst):
                return False
        return True
    def tolist(self):
        ret = []
        for item in self.items:
            ret.extend(item.tolist())
        return ret

class Tree:
    def __init__(self, course, string):
        self.course = course
        self.index = 0
        if not isinstance(string, str):
            self.prereq = []
        else:
            self.prereq = parse_prereq_string(string).tolist() 
            self.prereq[:] = [x for x in self.prereq if isinstance(x, Course)] #filter so only courses are present
            self.prereq = list(map(lambda x: Tree(x, get_prereq_string(x.subject, x.number)), self.prereq)) #convert the prereqs into trees
    def __str__(self, level = 1):
        add = "\n" + (" " * level)
        lst = []
        for item in self.prereq:
            lst.append(item.__str__(level + 1))
        return str(self.course) + add + add.join(lst)
    def pr(self):
        print(self.course)
        for item in self.prereq:
            item.pr()

