import json
from datetime import datetime

from django.core.files.storage import default_storage
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status
from .models import *


# Create your views here.
@api_view(['GET'])
def index(request):
    return HttpResponse("Connection successful", status=status.HTTP_200_OK)


@api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
def get_quiz(request, quiz_id):
    data = Quiz.objects(id=quiz_id)[0]
    data.quiz_id = quiz_id
    return HttpResponse(data.to_json(), status=status.HTTP_200_OK)


@api_view(['GET'])
def get_quizes(request):
    data = Quiz.objects()
    return HttpResponse(data.to_json(), status=status.HTTP_200_OK)


@api_view(['POST'])
def create_quiz(request):
    body = request.body
    new_quiz = Quiz.from_json(body)
    new_quiz.last_save = datetime.now()
    new_quiz.first_save = datetime.now()
    new_quiz.save()
    return HttpResponse(json.dumps({'id': str(new_quiz.id), 'last_save': str(new_quiz.last_save)}),
                        status=status.HTTP_201_CREATED)


@api_view(['PUT'])
def update_quiz(request, quiz_id):
    body = json.loads(request.body)
    Quiz.objects(id=quiz_id).update_one(**body, set__last_save=datetime.now())
    return HttpResponse(json.dumps({'last_save': str(datetime.now())}), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
def delete_quiz(request, quiz_id):
    Quiz.objects(id=quiz_id).delete()
    return HttpResponse(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def upload_image(request, quiz_id):
    context = request.POST.get('context')
    if context == 'preview':
        file = request.FILES['image']
        file_name = default_storage.save(f"{quiz_id}_preview_{file.name}", file)
        Quiz.objects(id=quiz_id).update_one(set__img_preview=file_name)

    elif context == 'bg':
        file = request.FILES['image']
        file_name = default_storage.save(f"{quiz_id}_bg_{file.name}", file)
        Quiz.objects(id=quiz_id).update_one(set__img_bg=file_name)

    elif context == 'option-img':
        file = request.FILES['image']
        question_index = int(request.POST.get('question_index'))
        option_index = int(request.POST.get('option_index'))
        print(option_index, question_index)
        file_name = default_storage.save(f"{quiz_id}_optionImg_{question_index}_{option_index}_{file.name}", file)

        img_options = list(Quiz.objects(id=quiz_id))[0]['questions'][question_index]['answers']['imgOptions']
        img_data = dict(img_options[option_index])
        img_data['file'] = file_name

        query = f'set__questions__{question_index}__answers__imgOptions__{option_index}'
        Quiz.objects(id=quiz_id).update_one(**{query: img_data})

    elif context == 'puzzle-img':
        file = request.FILES['image']
        question_index = int(request.POST.get('question_index'))
        file_name = default_storage.save(f"{quiz_id}_puzzleImg_{question_index}_{file.name}", file)
        query = f'set__questions__{question_index}__answers__puzzle__img'
        Quiz.objects(id=quiz_id).update_one(**{query: file_name})
    else:
        return HttpResponse(json.dumps({'error': 'Context is not defined'}), status=status.HTTP_400_BAD_REQUEST)

    return HttpResponse(json.dumps({'file_name': file_name}), status=status.HTTP_200_OK)


@api_view(['GET'])
def get_image(request, file_name):
    file = default_storage.open(file_name)
    response = HttpResponse(file.read())
    response['Content-Type'] = 'image/jpeg'
    response['Content-Disposition'] = 'inline;filename=' + file.name
    return response


@api_view(['POST'])
def send_answer(request, quiz_id):
    new_answer = Answer.from_json(request.body)
    new_answer.quiz_id = quiz_id
    new_answer.datestamp = datetime.now()
    result = calculate_result(answer=new_answer)
    new_answer.score = result['score']
    Quiz.objects(id=quiz_id).update(inc__answers_count=1)
    new_answer.save()
    return HttpResponse(json.dumps({'answer_id': str(new_answer.id), 'results': result}),
                        status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_statistics(request, quiz_id):
    answers = Answer.objects(quiz_id=quiz_id)
    results = []
    for answer in answers:
        result = calculate_result(answer=answer)
        results.append(result)

    return HttpResponse(json.dumps(results), status=status.HTTP_200_OK)


def calculate_result(answer_id=None, answer=None):
    if answer_id:
        answer = Answer.objects(id=answer_id)[0]
    quiz = Quiz.objects(id=answer.quiz_id)[0]
    questions = quiz['questions']
    questions_stats = []
    score = 0
    corrects_count = 0
    mode_1_trigger = False
    max_score = 0
    timer = answer['timer']

    def set_results(question_, result):
        nonlocal corrects_count, score, questions_stats
        if result:
            corrects_count += 1
            score += question_['settings']['addScoresPerAnswer']
        questions_stats.append({'question': question_['settings']['index'], 'correct': result})

    for question, answer in zip(questions, answer['options']):
        if question['settings']['mode'] == 0 or question['settings']['mode'] == 2:
            max_score += question['settings']['addScoresPerAnswer']
            set_results(question, question['answers']['correctOption']['index'] == answer['answer'])
        elif question['settings']['mode'] == 1:
            correct_answers = list(filter(lambda x: x['isCorrect'], question['answers']['options']))
            if question['settings']['scoreMode'] == 0:
                max_score += question['settings']['addScoresPerAnswer']
                set_results(question, correct_answers == answer['answers_checked'])
            elif question['settings']['scoreMode'] == 1:
                max_score += len(correct_answers) * question['settings']['addScoresPerAnswer']
                for a in answer['answers_checked']:
                    if a['isCorrect']:
                        mode_1_trigger = True
                        score += question['settings']['addScoresPerAnswer']
                if mode_1_trigger:
                    corrects_count += 1
                    questions_stats.append({'question': question['settings']['index'], 'correct': True})
                else:
                    questions_stats.append({'question': question['settings']['index'], 'correct': False})
        else:
            max_score += question['settings']['addScoresPerAnswer']
            set_results(question, True if answer['answer'] else False)

    return {'questions_stats': questions_stats, 'score': score, 'max_score': max_score, 'timer': timer,
            'corrects_count': corrects_count, 'questions_count': len(questions)}