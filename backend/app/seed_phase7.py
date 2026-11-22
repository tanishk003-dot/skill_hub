import logging
from datetime import datetime, timezone, timedelta
from app.core.database import SessionLocal, engine, Base
from app.models.quote import MotivationalQuote
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_assignment import AssessmentAssignment
from app.models.user import User, UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_phase7")

ADMIN_QUOTES = [
    ("Leadership is the capacity to translate vision into reality.", "Warren Bennis"),
    ("Before you are a leader, success is all about growing yourself. When you become a leader, success is all about growing others.", "Jack Welch"),
    ("A leader is one who knows the way, goes the way, and shows the way.", "John C. Maxwell"),
    ("Management is doing things right; leadership is doing the right things.", "Peter Drucker"),
    ("The greatest leader is not necessarily the one who does the greatest things. He is the one that gets the people to do the greatest things.", "Ronald Reagan"),
    ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
    ("To handle yourself, use your head; to handle others, use your heart.", "Eleanor Roosevelt"),
    ("Leadership and learning are indispensable to each other.", "John F. Kennedy"),
    ("Great leaders are almost always great simplifiers.", "Colin Powell"),
    ("The art of leadership is saying no, not saying yes. It is very easy to say yes.", "Tony Blair"),
    ("A genuine leader is not a searcher for consensus but a molder of consensus.", "Martin Luther King Jr."),
    ("Surround yourself with great people; delegate authority; get out of the way.", "Ronald Reagan"),
    ("The function of leadership is to produce more leaders, not more followers.", "Ralph Nader"),
    ("Earn your leadership every day.", "Michael Jordan"),
    ("True leadership lies in guiding others to success.", "Bill Gates"),
    ("You don't lead by hitting people over the head - that's assault, not leadership.", "Dwight D. Eisenhower"),
    ("A leader takes people where they want to go. A great leader takes people where they don't necessarily want to go, but ought to be.", "Rosalynn Carter"),
    ("The quality of a leader is reflected in the standards they set for themselves.", "Ray Kroc"),
    ("Outstanding leaders go out of their way to boost the self-esteem of their personnel.", "Sam Walton"),
    ("People ask the difference between a leader and a boss. The leader leads, and the boss drives.", "Theodore Roosevelt"),
    ("Leadership is not about a title or a designation. It's about impact, influence, and inspiration.", "Robin Sharma"),
    ("A good leader takes a little more than his share of the blame, a little less than his share of the credit.", "Arnold H. Glasow"),
    ("Leadership is unlocking people's potential to become better.", "Bill Bradley"),
    ("The challenge of leadership is to be strong, but not rude; be kind, but not weak.", "Jim Rohn"),
    ("If your actions inspire others to dream more, learn more, do more and become more, you are a leader.", "John Quincy Adams"),
    ("High-performing engineering teams are built on psychological safety and clear architectural vision.", "L&K Team"),
    ("Velocity without discipline creates legacy debt; lead with sustainable engineering excellence.", "L&K Team"),
    ("Great tech organizations empower builders by removing friction and clarifying accountability.", "L&K Team"),
    ("Align every engineering milestone with genuine user impact and operational reliability.", "L&K Team"),
    ("Culture is what happens when no one is watching; set the engineering standard by example.", "L&K Team")
]

MENTOR_QUOTES = [
    ("A mentor is someone who allows you to see the hope inside yourself.", "Oprah Winfrey"),
    ("Tell me and I forget, teach me and I may remember, involve me and I learn.", "Benjamin Franklin"),
    ("The delicate balance of mentoring someone is not creating them in your own image, but giving them the opportunity to create themselves.", "Steven Spielberg"),
    ("The mind is not a vessel to be filled, but a fire to be kindled.", "Plutarch"),
    ("In learning you will teach, and in teaching you will learn.", "Phil Collins"),
    ("Spoon feeding in the long run teaches us nothing but the shape of the spoon.", "E. M. Forster"),
    ("One child, one teacher, one book, one pen can change the world.", "Malala Yousafzai"),
    ("Teaching is the greatest act of optimism.", "Colleen Wilcox"),
    ("A good teacher can inspire hope, ignite the imagination, and instill a love of learning.", "Brad Henry"),
    ("Mentoring is a brain to pick, an ear to listen, and a push in the right direction.", "John C. Crosby"),
    ("We make a living by what we get, but we make a life by what we give.", "Winston Churchill"),
    ("If you want to lift yourself up, lift up someone else.", "Booker T. Washington"),
    ("The best way to predict your future is to create it.", "Peter Drucker"),
    ("I cannot teach anybody anything. I can only make them think.", "Socrates"),
    ("Knowledge increases by sharing but not by saving.", "Kamari aka Lyrikal"),
    ("A teacher affects eternity; he can never tell where his influence stops.", "Henry Adams"),
    ("It is the supreme art of the teacher to awaken joy in creative expression and knowledge.", "Albert Einstein"),
    ("Colleagues are a wonderful thing - but mentors, that's where the real work gets done.", "Junot Diaz"),
    ("Show me a successful individual and I'll show you someone who had real positive influences in his or her life.", "Denzel Washington"),
    ("Every great achiever is inspired by a great mentor.", "Lailah Gifty Akita"),
    ("Guide learners to discover answers rather than dictating solutions.", "L&K Team"),
    ("Patience with syntax errors unlocks deep architectural intuition.", "L&K Team"),
    ("Mentorship is not about having all the answers; it is about asking the illuminating questions.", "L&K Team"),
    ("Celebrate small breakthroughs: every clean refactor builds future senior engineers.", "L&K Team"),
    ("Give constructive feedback with clear code examples and empathetic context.", "L&K Team"),
    ("A mentee's mistake is today's best teaching moment.", "L&K Team"),
    ("Model the debugging discipline and root-cause analysis you want your engineers to practice.", "L&K Team"),
    ("Build confidence by letting candidates navigate edge cases independently.", "L&K Team"),
    ("The best mentors measure success by how quickly their mentees surpass them.", "L&K Team"),
    ("Continuous guidance turns promising apprentices into exceptional staff engineers.", "L&K Team")
]

ASE_QUOTES = [
    ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Experience is the name everyone gives to their mistakes.", "Oscar Wilde"),
    ("Code is like humor. When you have to explain it, it's bad.", "Cory House"),
    ("Simplicity is prerequisite for reliability.", "Edsger W. Dijkstra"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("The only way to learn a new programming language is by writing programs in it.", "Dennis Ritchie"),
    ("It's not that I'm so smart, it's just that I stay with problems longer.", "Albert Einstein"),
    ("Continuous improvement is better than delayed perfection.", "Mark Twain"),
    ("Premature optimization is the root of all evil.", "Donald Knuth"),
    ("Truth can only be found in one place: the code.", "Robert C. Martin"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
    ("Walking on water and developing software from a specification are easy if both are frozen.", "Edward V. Berard"),
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("Quality is not an act, it is a habit.", "Aristotle"),
    ("You miss 100% of the shots you don't take.", "Wayne Gretzky"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("The expert in anything was once a beginner.", "Helen Hayes"),
    ("It always seems impossible until it is done.", "Nelson Mandela"),
    ("Small daily improvements over time lead to stunning results.", "Robin Sharma"),
    ("Write unit tests before you think you need them.", "L&K Team"),
    ("Every bug fixed is a permanent upgrade to your diagnostic skill set.", "L&K Team"),
    ("Master the fundamentals of time complexity and data structures early.", "L&K Team"),
    ("Treat compiler warnings with the same respect as runtime panics.", "L&K Team"),
    ("Consistent daily coding practice compounds faster than intense weekend sprints.", "L&K Team"),
    ("Read others' open source code to cultivate idiomatic architectural intuition.", "L&K Team"),
    ("Don't fear breaking code in a sandbox - that's where true mastery begins.", "L&K Team"),
    ("A clean git history reflects a structured, disciplined engineering thought process.", "L&K Team"),
    ("Embrace code reviews as free masterclasses from senior teammates.", "L&K Team"),
    ("Focus on writing resilient, observable systems from day one.", "L&K Team")
]

CODING_QUESTIONS = [
    {
        "type": AssessmentType.LOGICAL_THINKING,
        "difficulty": QuestionDifficulty.EASY,
        "skill_category": "Data Structures & Algorithms",
        "question_text": "Array Element Sum: Calculate and return the sum of all elements in an integer array.",
        "question_type": QuestionType.CODING,
        "marks": 10,
        "problem_statement": (
            "Given a list of space-separated integers, compute and return the sum of all elements.\n\n"
            "### Input Format\n"
            "A single line of space-separated integers.\n\n"
            "### Output Format\n"
            "A single integer representing the sum.\n\n"
            "### Constraints\n"
            "- Array length between 1 and 10^4\n"
            "- -10^6 <= element <= 10^6"
        ),
        "allowed_languages": ["python", "javascript", "java"],
        "starter_code": {
            "python": "from typing import List\nimport sys\n\ndef solve(numbers: List[int]) -> int:\n    # Return the sum of numbers in the list\n    return sum(numbers)\n\nif __name__ == '__main__':\n    raw = sys.stdin.read().strip()\n    if raw:\n        nums = [int(x) for x in raw.split()]\n        print(solve(nums))\n    else:\n        print(0)",
            "javascript": "const fs = require('fs');\n\nfunction solve(numbers) {\n    // Return the sum of numbers in the array\n    return numbers.reduce((acc, curr) => acc + curr, 0);\n}\n\nconst raw = fs.readFileSync(0, 'utf-8').trim();\nif (raw) {\n    const nums = raw.split(/\\s+/).map(Number);\n    console.log(solve(nums));\n} else {\n    console.log(0);\n}",
            "java": "import java.util.Scanner;\n\npublic class Solution {\n    public static int solve(int[] numbers) {\n        int sum = 0;\n        for (int n : numbers) {\n            sum += n;\n        }\n        return sum;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int sum = 0;\n        while (sc.hasNextInt()) {\n            sum += sc.nextInt();\n        }\n        System.out.println(sum);\n    }\n}"
        },
        "sample_test_cases": [
            {"id": 1, "input": "1 2 3 4 5", "expected_output": "15"}
        ],
        "hidden_test_cases": [
            {"id": 2, "input": "-10 20 -5 15", "expected_output": "20", "marks": 5},
            {"id": 3, "input": "0 0 0", "expected_output": "0", "marks": 5}
        ],
        "time_limit_sec": 2.0,
        "memory_limit_mb": 256
    },
    {
        "type": AssessmentType.LOGICAL_THINKING,
        "difficulty": QuestionDifficulty.MEDIUM,
        "skill_category": "Algorithms & Strings",
        "question_text": "Valid Palindrome: Determine if a string is a palindrome considering alphanumeric characters only.",
        "question_type": QuestionType.CODING,
        "marks": 10,
        "problem_statement": (
            "A phrase is a palindrome if, after converting all uppercase letters into lowercase letters "
            "and removing all non-alphanumeric characters, it reads the same forward and backward.\n\n"
            "Print 'true' if it is a palindrome, or 'false' otherwise."
        ),
        "allowed_languages": ["python", "javascript", "java"],
        "starter_code": {
            "python": "import sys\n\ndef is_palindrome(s: str) -> bool:\n    clean = [c.lower() for c in s if c.isalnum()]\n    return clean == clean[::-1]\n\nif __name__ == '__main__':\n    raw = sys.stdin.read().strip()\n    print('true' if is_palindrome(raw) else 'false')",
            "javascript": "const fs = require('fs');\n\nfunction isPalindrome(s) {\n    const clean = s.toLowerCase().replace(/[^a-z0-9]/g, '');\n    return clean === clean.split('').reverse().join('');\n}\n\nconst raw = fs.readFileSync(0, 'utf-8').trim();\nconsole.log(isPalindrome(raw) ? 'true' : 'false');",
            "java": "import java.util.Scanner;\n\npublic class Solution {\n    public static boolean isPalindrome(String s) {\n        StringBuilder sb = new StringBuilder();\n        for (char c : s.toCharArray()) {\n            if (Character.isLetterOrDigit(c)) {\n                sb.append(Character.toLowerCase(c));\n            }\n        }\n        String clean = sb.toString();\n        return clean.equals(sb.reverse().toString());\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String line = sc.hasNextLine() ? sc.nextLine() : \"\";\n        System.out.println(isPalindrome(line) ? \"true\" : \"false\");\n    }\n}"
        },
        "sample_test_cases": [
            {"id": 1, "input": "racecar", "expected_output": "true"}
        ],
        "hidden_test_cases": [
            {"id": 2, "input": "hello world", "expected_output": "false", "marks": 5},
            {"id": 3, "input": "A man a plan a canal Panama", "expected_output": "true", "marks": 5}
        ],
        "time_limit_sec": 2.0,
        "memory_limit_mb": 256
    },
    {
        "type": AssessmentType.LOGICAL_THINKING,
        "difficulty": QuestionDifficulty.EASY,
        "skill_category": "Logic & Flow Control",
        "question_text": "FizzBuzz Sequence: Output numbers from 1 to N with Fizz, Buzz, or FizzBuzz.",
        "question_type": QuestionType.CODING,
        "marks": 10,
        "problem_statement": (
            "Given an integer N, print each value from 1 to N on a new line.\n"
            "- Multiples of 3 print 'Fizz'\n"
            "- Multiples of 5 print 'Buzz'\n"
            "- Multiples of both print 'FizzBuzz'\n"
            "- Otherwise print the number."
        ),
        "allowed_languages": ["python", "javascript"],
        "starter_code": {
            "python": "import sys\n\ndef fizzbuzz(n: int):\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n            print('FizzBuzz')\n        elif i % 3 == 0:\n            print('Fizz')\n        elif i % 5 == 0:\n            print('Buzz')\n        else:\n            print(i)\n\nif __name__ == '__main__':\n    raw = sys.stdin.read().strip()\n    if raw:\n        fizzbuzz(int(raw))",
            "javascript": "const fs = require('fs');\n\nfunction fizzbuzz(n) {\n    for (let i = 1; i <= n; i++) {\n        if (i % 15 === 0) console.log('FizzBuzz');\n        else if (i % 3 === 0) console.log('Fizz');\n        else if (i % 5 === 0) console.log('Buzz');\n        else console.log(i);\n    }\n}\n\nconst raw = fs.readFileSync(0, 'utf-8').trim();\nif (raw) {\n    fizzbuzz(parseInt(raw, 10));\n}"
        },
        "sample_test_cases": [
            {"id": 1, "input": "5", "expected_output": "1\n2\nFizz\n4\nBuzz"}
        ],
        "hidden_test_cases": [
            {"id": 2, "input": "3", "expected_output": "1\n2\nFizz", "marks": 5},
            {"id": 3, "input": "15", "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz", "marks": 5}
        ],
        "time_limit_sec": 2.0,
        "memory_limit_mb": 256
    }
]

def seed_phase7_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Seed Quotes
        existing_quotes_count = db.query(MotivationalQuote).count()
        if existing_quotes_count == 0:
            logger.info("Seeding 90 Motivational Quotes (30 Admin, 30 Mentor, 30 ASE)...")
            quotes_to_add = []
            for text, author in ADMIN_QUOTES:
                quotes_to_add.append(MotivationalQuote(role="ADMIN", text=text, author=author, is_active=True, is_demo=True))
            for text, author in MENTOR_QUOTES:
                quotes_to_add.append(MotivationalQuote(role="MENTOR", text=text, author=author, is_active=True, is_demo=True))
            for text, author in ASE_QUOTES:
                quotes_to_add.append(MotivationalQuote(role="ASE", text=text, author=author, is_active=True, is_demo=True))
            db.bulk_save_objects(quotes_to_add)
            db.commit()
            logger.info("Successfully seeded 90 motivational quotes!")

        # 2. Seed Coding Questions
        coding_q_count = db.query(QuestionBank).filter(QuestionBank.question_type == QuestionType.CODING).count()
        if coding_q_count == 0:
            logger.info("Seeding 3 Sample Coding Questions...")
            saved_coding_qs = []
            for q_data in CODING_QUESTIONS:
                q = QuestionBank(
                    type=q_data["type"],
                    difficulty=q_data["difficulty"],
                    skill_category=q_data["skill_category"],
                    question_text=q_data["question_text"],
                    question_type=q_data["question_type"],
                    options=[],
                    correct_answers=[],
                    marks=q_data["marks"],
                    problem_statement=q_data["problem_statement"],
                    allowed_languages=q_data["allowed_languages"],
                    starter_code=q_data["starter_code"],
                    sample_test_cases=q_data["sample_test_cases"],
                    hidden_test_cases=q_data["hidden_test_cases"],
                    time_limit_sec=q_data["time_limit_sec"],
                    memory_limit_mb=q_data["memory_limit_mb"]
                )
                db.add(q)
                saved_coding_qs.append(q)
            db.commit()
            for q in saved_coding_qs:
                db.refresh(q)
            logger.info("Successfully seeded 3 Coding Questions!")

            # 3. Add a Coding Section to Sample Assessment (Mixed Assessment: MCQ + Coding)
            sample_assessment = db.query(Assessment).first()
            if sample_assessment and saved_coding_qs:
                coding_section = AssessmentSection(
                    assessment_id=sample_assessment.id,
                    title="Section 3: Hands-on Coding",
                    timer_minutes=30,
                    order_index=2
                )
                db.add(coding_section)
                db.flush()

                for idx, cq in enumerate(saved_coding_qs):
                    asq = AssessmentSectionQuestion(
                        section_id=coding_section.id,
                        question_id=cq.id,
                        order_index=idx
                    )
                    db.add(asq)
                
                # Update total duration
                sample_assessment.total_duration_minutes = (sample_assessment.total_duration_minutes or 30) + 30
                db.commit()
                logger.info(f"Added Mixed Coding Section to Assessment #{sample_assessment.id}!")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding phase 7: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_phase7_data()
