import os
import pickle
from collections import OrderedDict
from typing import List
from operators import operators
from shunting_yard import ShuntingYard


def perform_AND(left: List[int], right: List[int]) -> List[int]:
    l_pos = 0
    r_pos = 0
    result = []

    while l_pos < len(left) and r_pos < len(right):
        if left[l_pos] == right[r_pos]:
            result.append(left[l_pos])
            l_pos += 1
            r_pos += 1
        elif left[l_pos] < right[r_pos]:
            l_pos += 1
        else:
            r_pos += 1

    return result


def perform_OR(left: List[int], right: List[int]) -> List[int]:
    l_pos = 0
    r_pos = 0
    result = []

    while l_pos < len(left) or r_pos < len(right):
        if l_pos == len(left):
            result += right[r_pos:]
            break
        elif r_pos == len(right):
            result += left[l_pos:]
            break

        elif left[l_pos] == right[r_pos]:
            result.append(left[l_pos])
            l_pos += 1
            r_pos += 1
        elif left[l_pos] < right[r_pos]:
            result.append(left[l_pos])
            l_pos += 1
        else:
            result.append(right[r_pos])
            r_pos += 1

    return result


def perform_NOT(exclude: List[int], all_documents) -> List[int]:
    result = [docID for docID in all_documents if (docID not in exclude)]
    result.sort()
    return result


# Начинаем
if not os.path.exists('final_block.txt'):
    print("ERROR: final_block.txt not found. Build index first?")
    sys.exit(1)
else:
    print('Loading index to memory...')
    index = OrderedDict()

    # Читаем индекс с диска в упорядоченный словарь
    with open('final_block.txt') as f:
        for line in f:
            term = line[:-1].split(' -> ')[0]
            docIDs = list(line[:-1].split(' -> ')[1][1:-1].split(', '))
            index[term] = docIDs

    # Читаем с диска словарь, отображающий docID в имя документа
    with open('docID_doc_map.pickle', 'rb') as f:
        docID_doc_map = pickle.load(f)

    while True:
        print('\nEnter the query or \'/exit\':')
        query = str(input('QUERY: '))
        if query == '/exit':
            break
        else:
            input_tokens = query.split(' ')

            # Представим запрос в обратной польской нотации
            # Так с ними будет проще работать
            rpn = ShuntingYard(input_tokens).get_RPN()

        stack = []
        all_document_ids = [docID for docID in docID_doc_map.keys()]

        for token in rpn:
            if token not in operators:
                docIDs = index[token] if token in index else []
                docIDs = [int(docID[1:-1]) for docID in docIDs]
                stack.append(docIDs)
            else:
                if token == "AND":
                    right_operand = stack.pop()
                    left_operand = stack.pop()
                    stack.append(perform_AND(left_operand, right_operand))
                elif token == "OR":
                    right_operand = stack.pop()
                    left_operand = stack.pop()
                    stack.append(perform_OR(left_operand, right_operand))
                elif token == "NOT":
                    operand = stack.pop()
                    stack.append(perform_NOT(operand, all_document_ids))

        print('Found \'{}\' documents:'.format(len(stack[0])))
        doc_names = []
        for docID in stack[0]:
            doc_names.append(docID_doc_map[int(docID)])
        for doc in doc_names:
            print('  {}'.format(doc))
