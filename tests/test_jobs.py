import app as work_app


def test_jobs_page_loads_and_lists_entries():
    with work_app.app.test_client() as client:
        with client.session_transaction() as session:
            session['csrf_token'] = 'test'
        response = client.get('/jobs')
        assert response.status_code == 200
        assert b'Ish qidiruv va ish berish' in response.data


def test_job_post_creates_new_listing():
    with work_app.app.test_client() as client:
        with client.session_transaction() as session:
            session['csrf_token'] = 'test'

        response = client.post(
            '/jobs',
            data={
                'action': 'post_job',
                'employer_name': 'Test firma',
                'title': 'Sotuvchi',
                'category': 'Savdo',
                'age': '20-35',
                'location': 'Fargona',
                'phone': '+998901112233',
                'salary': "2 000 000 so'm",
                'description': 'Mijozlar bilan ishlash va savat yuritish.',
                'csrf_token': 'test',
            },
        )
        assert response.status_code == 302

        page = client.get('/jobs')
        assert b'Test firma' in page.data
        assert b'Fargona' in page.data
