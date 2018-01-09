import prereq
course_schedule = []
while (True):
    cmd = input()
    if cmd == "q":
            break
    elif cmd == "add":
        subject = input("Subject:\n").upper()
        number = input("Course Number:\n")
        #validate input
        pr = prereq.get_prereq_string(subject, number)
        if not isinstance(pr, str):
            if pr == 0:
                print("Invalid subject")
            elif pr == 1:
                print("Course not found")
            continue
        course_schedule.append(prereq.Tree(prereq.Course(subject, number), pr))
    elif cmd == "print":
        for course in course_schedule:
            print(course)
